"""
Everything Gemini-related: client setup, the data-question keyword gate, the
forced-tool-call flow (needed because AUTO mode unreliably skips tool calls),
and the top-level _ask_gemini_sync/get_gemini_response entrypoints used by
the webhook handler.
"""
import json
import os
import time
import datetime
import urllib.request
import urllib.error
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types

from app import config
from app.services import klive_service, pending_action_service
import flex_builder

_QUOTA_FALLBACK_TEXT = "ขออภัยครับ ตอนนี้ระบบ AI ใช้งานหนาแน่นเกินโควตาชั่วคราว (429) กรุณาลองใหม่ในอีก 1-2 นาทีครับ"


def _is_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "resource_exhausted" in text
        or "429" in text
        or "rate limit" in text
        or "quota" in text
    )


def _deepseek_chat(payload: dict) -> dict:
    base = config.DEEPSEEK_BASE_URL.rstrip("/")
    url = f"{base}/chat/completions"
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
    }
    if config.DEEPSEEK_SITE_URL:
        headers["HTTP-Referer"] = config.DEEPSEEK_SITE_URL
    if config.DEEPSEEK_APP_NAME:
        headers["X-Title"] = config.DEEPSEEK_APP_NAME

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            body_text = e.read().decode("utf-8", errors="ignore")
            detail = f" {body_text[:400]}"
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {e.reason}.{detail}") from e

    return json.loads(raw)


def _build_klive_tool_runtime(user_id: str):
    captured = {}

    def run_klive_command(command_args: list[str]) -> str:
        subcommand = command_args[0] if command_args else ""
        args = list(command_args)

        if subcommand == "k-my-projects":
            projects = klive_service.list_my_managed_projects()
            captured["kind"] = "k-projects"
            captured["data"] = projects
            output = json.dumps(projects, ensure_ascii=False)
            print(f"🔧 tool call: {args} -> {len(output)} chars")
            return output

        if subcommand in DESTRUCTIVE_SUBCOMMANDS:
            summary_text = _build_confirmation_summary(subcommand, args)
            action_id = pending_action_service.create_pending_action(user_id, args, summary_text)
            captured["confirm_pending"] = {"action_id": action_id, "summary_text": summary_text}
            print(f"🛑 Destructive action '{subcommand}' held for confirmation (action_id={action_id})")
            return "รอการยืนยันจากผู้ใช้ก่อนดำเนินการ"

        if subcommand in klive_service.RAW_CAPABLE_SUBCOMMANDS and "--raw" not in args:
            args.append("--raw")

        output = klive_service.run_klive(args)
        print(f"🔧 tool call: {args} -> {len(output)} chars")

        try:
            data = json.loads(output)
            captured["kind"] = subcommand
            captured["data"] = data
        except (json.JSONDecodeError, TypeError):
            print(f"⚠️ Non-JSON output from '{subcommand}' (not captured for Flex): {output[:200]!r}")
        return output

    run_klive_command.__doc__ = (
        "Execute a klive-tasks CLI command to manage tasks, projects, milestones, sprints, "
        "or users in the dh-task system. `command_args` must be the subcommand followed by "
        "its exact flags — only use the subcommands and flags listed below, never invent new ones. "
        + KLIVE_SKILL_DOC
    )
    return captured, run_klive_command


def _postprocess_tool_result(captured: dict, text: str) -> dict:
    if "confirm_pending" in captured:
        return {"confirm_pending": captured["confirm_pending"]}

    flex = None
    if "data" in captured:
        try:
            flex = flex_builder.build_flex_for(
                captured["kind"], captured["data"], resolve_user=klive_service.resolve_user_name
            )
        except Exception as e:
            print(f"⚠️ Flex build error for kind={captured.get('kind')}: {e}")

    return {"text": text or "เรียบร้อยครับ", "flex": flex}


def _ask_deepseek_sync(user_message: str, user_id: str) -> dict:
    if not config.DEEPSEEK_API_KEY:
        return {
            "text": "⚠️ ยังไม่ได้ตั้งค่า DEEPSEEK_API_KEY (หรือ OPENROUTER_API_KEY)",
            "flex": None,
        }

    captured, run_klive_command = _build_klive_tool_runtime(user_id)
    self_user_id = klive_service.resolve_self_user_id()
    self_instruction = (
        f"ถ้าผู้ใช้พูดถึงตัวเองให้ใช้ user_id={self_user_id} เป็น --assignee ได้ทันที\n"
        "และถ้าถามโปรเจกต์ที่ตัวเองดูแลให้เรียก k-my-projects\n"
        if self_user_id else ""
    )
    system_instruction = (
        "คุณคือ Greenman ผู้ช่วยจัดการงาน dh-task ทาง LINE ตอบภาษาไทยสุภาพสั้นกระชับ\n"
        "คำถามเกี่ยวกับข้อมูลจริงใน dh-task ต้องเรียก run_klive_command ก่อนเสมอ ห้ามเดา\n"
        f"{self_instruction}"
    )

    tool_spec = {
        "type": "function",
        "function": {
            "name": "run_klive_command",
            "description": run_klive_command.__doc__ or "Run klive command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command_args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "subcommand and flags, e.g. ['k-list','--status','todo']",
                    }
                },
                "required": ["command_args"],
            },
        },
    }

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_message},
    ]

    payload = {
        "model": config.DEEPSEEK_MODEL,
        "messages": messages,
        "tools": [tool_spec],
        "temperature": 0.3,
    }
    if _looks_like_data_question(user_message):
        payload["tool_choice"] = {"type": "function", "function": {"name": "run_klive_command"}}

    try:
        first = _deepseek_chat(payload)
        choices = first.get("choices") or []
        if not choices:
            return {"text": "ขออภัยครับ ไม่สามารถสร้างคำตอบได้ในขณะนี้", "flex": None}

        first_message = choices[0].get("message") or {}
        tool_calls = first_message.get("tool_calls") or []
        if not tool_calls:
            return {"text": first_message.get("content") or "เรียบร้อยครับ", "flex": None}

        messages.append(first_message)
        for tc in tool_calls:
            fn = (tc.get("function") or {}).get("name", "")
            arg_text = (tc.get("function") or {}).get("arguments") or "{}"
            try:
                parsed = json.loads(arg_text)
            except Exception:
                parsed = {}
            command_args = parsed.get("command_args") or []
            if fn != "run_klive_command":
                tool_result = "unsupported tool"
            else:
                tool_result = run_klive_command(command_args)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": tool_result,
                }
            )

        second = _deepseek_chat(
            {
                "model": config.DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": 0.3,
            }
        )
        second_choices = second.get("choices") or []
        final_text = "เรียบร้อยครับ"
        if second_choices:
            final_text = (second_choices[0].get("message") or {}).get("content") or final_text
        return _postprocess_tool_result(captured, final_text)
    except Exception as e:
        text = str(e).lower()
        if "401" in text or "unauthorized" in text:
            return {"text": "ขออภัยครับ คีย์ของผู้ให้บริการ AI ไม่ถูกต้องหรือหมดอายุ (401)", "flex": None}
        if _is_quota_error(e):
            print(f"⚠️ DeepSeek quota/rate-limit hit: {e}")
            return {"text": _QUOTA_FALLBACK_TEXT, "flex": None}
        return {"text": f"ขออภัยครับ เกิดข้อผิดพลาดทางเทคนิค: {str(e)}", "flex": None}

# The dh-task team's own SKILL.md (same one they use for their own Claude
# Code / Cursor setup) is the source of truth for which klive-tasks
# subcommands/flags exist. Loading it here instead of hand-duplicating the
# command reference means updates to that file (new subcommands, new flags,
# fixed examples) automatically improve Gemini's tool-calling accuracy
# without a code change. Falls back to a short built-in reference if the
# file is missing so the bot still works at all.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_KLIVE_SKILL_PATH = os.path.join(_REPO_ROOT, "docs", "klive-tasks-SKILL.md")

_FALLBACK_KLIVE_DOC = (
    "k-users, k-projects, k-get-project, k-list, k-get, k-subtasks, k-stats, "
    "k-create, k-update, k-delete, k-milestone-list, k-milestone-get, "
    "k-milestone-create, k-milestone-update, k-milestone-delete. "
    "(docs/klive-tasks-SKILL.md was missing at startup — using this bare-bones "
    "fallback list, so unfamiliar flags may not work correctly.)"
)


def _load_klive_skill_doc() -> str:
    try:
        with open(_KLIVE_SKILL_PATH, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"⚠️ Could not load {_KLIVE_SKILL_PATH}, using fallback tool doc: {e}")
        return _FALLBACK_KLIVE_DOC

    # Strip the YAML frontmatter (--- name/description ... ---) — that part
    # is metadata for Claude Code's own skill loader, not useful as a Gemini
    # tool description.
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]
    return text.strip()


KLIVE_SKILL_DOC = _load_klive_skill_doc()

# Subcommands that permanently delete or overwrite existing dh-task data.
# Gemini resolving one of these does NOT execute it immediately — see
# _build_confirmation_summary / the interception in run_klive_command below.
DESTRUCTIVE_SUBCOMMANDS = {"k-delete", "k-milestone-delete", "k-update", "k-milestone-update"}

# arg flag -> best-effort JSON field name on the fetched entity, used to show
# "from X to Y" in the confirmation message for k-update/k-milestone-update.
_UPDATE_FIELD_MAP = {
    "--title": "title",
    "--description": "description",
    "--status": "status",
    "--priority": "priority",
    "--due-date": "due_date",
    "--start-date": "start_date",
    "--assigned-to": "assigned_to",
    "--milestone-id": "milestone_id",
}


def _args_to_dict(command_args: list[str]) -> dict[str, str]:
    """['--id', 'abc', '--status', 'done'] -> {'--id': 'abc', '--status': 'done'}"""
    d = {}
    i = 1  # skip the subcommand itself
    while i < len(command_args) - 1:
        if command_args[i].startswith("--"):
            d[command_args[i]] = command_args[i + 1]
            i += 2
        else:
            i += 1
    return d


def _build_confirmation_summary(subcommand: str, command_args: list[str]) -> str:
    """Builds the Thai confirmation text shown before a destructive action
    actually runs. Best-effort: falls back to a generic message if the
    entity can't be fetched (e.g. bad id) rather than blocking confirmation
    entirely — the user still gets a chance to cancel either way."""
    args = _args_to_dict(command_args)
    entity_id = args.get("--id", "")

    if subcommand == "k-delete":
        try:
            raw = klive_service.run_klive(["k-get", "--id", entity_id, "--raw"])
            data = json.loads(raw)
            title = data.get("title") or data.get("friendly_id") or entity_id
        except Exception:
            title = entity_id
        return f'ต้องการลบงาน "{title}" ใช่ไหมครับ? ลบแล้วกู้คืนไม่ได้นะครับ'

    if subcommand == "k-milestone-delete":
        project_id = args.get("--project-id", "")
        try:
            raw = klive_service.run_klive(["k-milestone-get", "--project-id", project_id, "--id", entity_id, "--raw"])
            data = json.loads(raw)
            title = data.get("title") or entity_id
        except Exception:
            title = entity_id
        return f'ต้องการลบ Milestone "{title}" ใช่ไหมครับ? ลบแล้วกู้คืนไม่ได้นะครับ'

    if subcommand in ("k-update", "k-milestone-update"):
        if subcommand == "k-update":
            fetch_args = ["k-get", "--id", entity_id, "--raw"]
        else:
            fetch_args = ["k-milestone-get", "--project-id", args.get("--project-id", ""), "--id", entity_id, "--raw"]
        try:
            raw = klive_service.run_klive(fetch_args)
            current = json.loads(raw)
        except Exception:
            current = {}
        title = current.get("title") or entity_id

        changes = []
        for flag, json_key in _UPDATE_FIELD_MAP.items():
            if flag not in args:
                continue
            new_value = args[flag]
            old_value = current.get(json_key)
            if old_value is not None and str(old_value) != str(new_value):
                changes.append(f'- {json_key}: "{old_value}" → "{new_value}"')
            elif old_value is None:
                changes.append(f'- {json_key}: → "{new_value}"')
        changes_text = "\n".join(changes) if changes else "(ไม่พบการเปลี่ยนแปลงที่ชัดเจน)"
        return f'ต้องการแก้ไขงาน "{title}" ดังนี้ใช่ไหมครับ?\n{changes_text}'

    return "ต้องการดำเนินการนี้ใช่ไหมครับ?"

gemini_client = None
if config.LLM_PROVIDER == "gemini" and config.GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
elif config.LLM_PROVIDER == "gemini":
    print("⚠️ Warning: GEMINI_API_KEY is not set. AI features will be unavailable.")


# Best-effort gate for "does this message need real dh-task data". Prompting
# Gemini nicely to always call the tool for data questions turned out to be
# unreliable in practice (it sometimes answers from general knowledge
# instead) — so for anything that looks like a data question we force a tool
# call ourselves rather than leaving it to the model's judgement.
DATA_QUERY_KEYWORDS = (
    "โปรเจ", "project", "งาน", "task", "ทาสก์",  # "โปรเจ" catches โปรเจกต์/โปรเจ็กต์/โปรเจค/โปรเจ็ค spelling variants
    "มายล์สโตน", "ไมล์สโตน", "milestone",
    "สถิติ", "stat", "สถานะ", "status",
    "กำหนดส่ง", "due", "deadline",
    "มอบหมาย", "รับผิดชอบ", "assign",
    "สมาชิก", "สปรินท์", "sprint",
    "ใคร", "user", "ผู้ใช้", "k-",
)


def _looks_like_data_question(text: str) -> bool:
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in DATA_QUERY_KEYWORDS)


_THAI_DAYS = ["วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี", "วันศุกร์", "วันเสาร์", "วันอาทิตย์"]
_THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


def _current_thai_datetime_str() -> str:
    now = datetime.datetime.now(ZoneInfo("Asia/Bangkok"))
    day_name = _THAI_DAYS[now.weekday()]
    month_name = _THAI_MONTHS[now.month - 1]
    buddhist_year = now.year + 543
    return (
        f"{day_name}ที่ {now.day} {month_name} พ.ศ. {buddhist_year} "
        f"(หรือ {now.strftime('%Y-%m-%d')} เวลา {now.strftime('%H:%M')} น. ตามเขตเวลาไทย)"
    )


def _forced_tool_turn(user_message: str, system_instruction: str, tool_fn) -> str:
    """
    Forces exactly one call to tool_fn instead of leaving it to the model's
    judgement. We can't just set tool_config mode=ANY on a normal
    automatic-function-calling chat: the SDK reuses the same config for every
    internal round trip, so ANY would keep forcing function calls forever.
    Instead we disable automatic function calling, force+execute exactly one
    call ourselves, then make a second, unforced call so the model can
    produce a normal natural-language reply from the result.
    """
    forced_config = types.GenerateContentConfig(
        tools=[tool_fn],
        system_instruction=system_instruction,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.ANY,
            )
        ),
    )
    user_content = types.Content(role="user", parts=[types.Part.from_text(text=user_message)])

    t0 = time.time()
    first = gemini_client.models.generate_content(
        model=config.GEMINI_MODEL, contents=[user_content], config=forced_config,
    )
    print(f"⏱️ Gemini call #1 (forced tool selection) took {time.time() - t0:.2f}s")
    if not first.candidates or not first.candidates[0].content or not first.candidates[0].content.parts:
        return first.text or "ขออภัยครับ ไม่พบข้อมูล"

    part = first.candidates[0].content.parts[0]
    if not getattr(part, "function_call", None):
        return first.text or "ขออภัยครับ ไม่พบข้อมูล"

    fc = part.function_call
    call_args = dict(fc.args or {})
    print(f"🔨 forced tool call: {fc.name}({call_args})")
    t1 = time.time()
    tool_result = tool_fn(**call_args)
    print(f"⏱️ tool execution (subprocess to dh-task API) took {time.time() - t1:.2f}s")

    contents = [
        user_content,
        first.candidates[0].content,
        types.Content(
            role="user",
            parts=[types.Part.from_function_response(name=fc.name, response={"result": tool_result})],
        ),
    ]
    t2 = time.time()
    second = gemini_client.models.generate_content(
        model=config.GEMINI_MODEL, contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_instruction),
    )
    print(f"⏱️ Gemini call #2 (final summary) took {time.time() - t2:.2f}s")
    return second.text or "เรียบร้อยครับ"


def _ask_gemini_sync(user_message: str, user_id: str) -> dict:
    """
    Blocking call into the Gemini API. Returns
    {"text": <reply>, "flex": <flex payload or None>} normally, or
    {"confirm_pending": {"action_id": ..., "summary_text": ...}} when Gemini
    resolved a destructive action (k-delete/k-update/etc.) — the caller
    (webhook_handler) is responsible for turning that into a confirm/cancel
    Quick Reply instead of executing anything yet.
    """
    if config.LLM_PROVIDER != "gemini":
        return {
            "text": (
                f"⚠️ LLM_PROVIDER={config.LLM_PROVIDER!r} ยังไม่รองรับในเวอร์ชันนี้ "
                "(รองรับเฉพาะ 'gemini')"
            ),
            "flex": None,
        }

    if not gemini_client:
        return {"text": "⚠️ ไม่สามารถใช้งาน AI ได้ในขณะนี้ เนื่องจากยังไม่ได้กรอก GEMINI_API_KEY", "flex": None}

    captured = {}

    def run_klive_command(command_args: list[str]) -> str:
        subcommand = command_args[0] if command_args else ""
        args = list(command_args)

        if subcommand == "k-my-projects":
            # Virtual subcommand — no real CLI equivalent. Filtering
            # member_roles by a hardcoded role_id isn't something to leave to
            # the model (it can't see/interpret the raw member_roles dict
            # reliably), so this is deterministic Python, same logic used by
            # the "งาน" shortcut in webhook_handler.py. Reusing it here lets
            # free-form questions ("โปรเจกต์ที่ผมเป็น PM มีอะไรบ้าง") get the
            # same correct answer as the exact shortcut.
            projects = klive_service.list_my_managed_projects()
            captured["kind"] = "k-projects"
            captured["data"] = projects
            output = json.dumps(projects, ensure_ascii=False)
            print(f"🔧 tool call: {args} -> {len(output)} chars")
            return output

        if subcommand in DESTRUCTIVE_SUBCOMMANDS:
            summary_text = _build_confirmation_summary(subcommand, args)
            action_id = pending_action_service.create_pending_action(user_id, args, summary_text)
            captured["confirm_pending"] = {"action_id": action_id, "summary_text": summary_text}
            print(f"🛑 Destructive action '{subcommand}' held for confirmation (action_id={action_id})")
            # This becomes the function_response for the (discarded) second
            # Gemini call — its actual content doesn't matter since
            # _ask_gemini_sync overrides the return value once confirm_pending
            # is set, but it must be a string so the SDK is happy.
            return "รอการยืนยันจากผู้ใช้ก่อนดำเนินการ"

        if subcommand in klive_service.RAW_CAPABLE_SUBCOMMANDS and "--raw" not in args:
            args.append("--raw")

        output = klive_service.run_klive(args)
        print(f"🔧 tool call: {args} -> {len(output)} chars")

        try:
            data = json.loads(output)
            captured["kind"] = subcommand
            captured["data"] = data
        except (json.JSONDecodeError, TypeError):
            print(f"⚠️ Non-JSON output from '{subcommand}' (not captured for Flex): {output[:200]!r}")

        return output

    # Docstring drives the Gemini function-calling schema (this is what tells
    # the model which subcommands/flags exist), so it's set here from the
    # loaded SKILL.md content instead of being a hardcoded literal — see
    # KLIVE_SKILL_DOC / _load_klive_skill_doc() above.
    run_klive_command.__doc__ = (
        "Execute a klive-tasks CLI command to manage tasks, projects, milestones, sprints, "
        "or users in the dh-task system. `command_args` must be the subcommand followed by "
        "its exact flags — only use the subcommands and flags listed below, never invent new ones. "
        "If the user names a project but you don't have its id yet, call k-projects first to find "
        "it (match by name), then use that project's \"id\" field for follow-up calls.\n\n"
        + KLIVE_SKILL_DOC
        + "\n\n## k-my-projects (custom — not part of the official CLI/SKILL.md above)\n\n"
        "```\nk-my-projects\n```\n\n"
        "Takes no flags. Returns only the projects where the current LINE user's dh-task "
        "account holds the PM role (per each project's member_roles field), with each "
        "project's milestones already fetched and attached. Use this instead of k-projects "
        "whenever the user asks about projects they manage, are PM of, or are responsible "
        "for (e.g. 'โปรเจกต์ที่ผมเป็น PM มีอะไรบ้าง', 'โปรเจกต์ที่ผมดูแล', 'projects I manage') — "
        "do not call k-projects and try to filter member_roles yourself, the role_id isn't "
        "something you can reliably interpret from the raw JSON.\n\n"
        + "\n\nArgs:\n"
        "    command_args: The subcommand and its flags as separate list items, e.g.\n"
        '        ["k-milestone-list", "--project-id", "abc123"] or ["k-my-projects"].'
    )

    self_user_id = klive_service.resolve_self_user_id()
    self_instruction = (
        f"ถ้าผู้ใช้พูดถึงตัวเอง (เช่น 'ของฉัน', 'ผม', 'ฉัน', 'ตัวเอง', 'ตนเอง') ในบริบทงาน/โปรเจกต์/มอบหมาย "
        f"ให้ใช้ user_id = \"{self_user_id}\" (อีเมล {config.SELF_EMAIL}) เป็นค่า --assignee ได้เลยทันที "
        "ไม่ต้องเรียก k-users ค้นหาซ้ำอีก\n\n"
        "ถ้าผู้ใช้ถามถึงโปรเจกต์ที่ตัวเองเป็น PM/ดูแล/รับผิดชอบ (ไม่ใช่แค่ถามงานที่ได้รับมอบหมาย) "
        "ให้เรียก run_klive_command(command_args=['k-my-projects']) แทนการเรียก k-projects ธรรมดา\n\n"
        if self_user_id else ""
    )

    system_instruction = (
        "คุณคือ 'Greenman' ผู้ช่วยจัดการงานในระบบ dh-task ผ่านไลน์\n\n"
        f"วันนี้คือ {_current_thai_datetime_str()} — ใช้ข้อมูลนี้ตอบคำถามทั่วไปเกี่ยวกับวันที่/เวลาได้เลย "
        "ไม่ต้องเดาหรือปฏิเสธว่าไม่รู้\n\n"
        "กฎสำคัญที่สุด: คุณไม่มีข้อมูลจริงของ tasks/projects/milestones/users อยู่ในตัวเองเลย "
        "ถ้าผู้ใช้ถามอะไรที่เกี่ยวกับข้อมูลจริงในระบบ (มีโปรเจกต์/งานอะไรบ้าง, สถานะ, milestone, "
        "ใครรับผิดชอบ, กำหนดส่ง, สถิติ ฯลฯ) คุณต้องเรียกใช้ run_klive_command ก่อนเสมอ "
        "ห้ามตอบจากความจำ ห้ามเดา ห้ามสร้างข้อมูล/ชื่อโปรเจกต์ขึ้นมาเองเด็ดขาด แม้จะดูมั่นใจแค่ไหนก็ตาม\n\n"
        f"{self_instruction}"
        "ตัวอย่างคำถามที่ต้องเรียกเครื่องมือก่อนตอบทุกครั้ง: "
        "'มีโปรเจกต์อะไรบ้าง', 'โปรเจกต์ X มี milestone อะไรบ้าง', 'งานของฉันมีอะไรบ้าง', "
        "'ใครรับผิดชอบงานนี้', 'สรุปสถิติงานหน่อย', 'งานนี้กำหนดส่งเมื่อไหร่'\n"
        "ถ้าผู้ใช้พูดถึงชื่อโปรเจกต์แต่คุณยังไม่รู้ project_id ให้เรียก k-projects ก่อนเพื่อค้นหา แล้วค่อยใช้ id ที่ได้เรียกคำสั่งถัดไป\n\n"
        "ที่ไม่ต้องเรียกเครื่องมือ: ทักทาย, ขอบคุณ, คำถามทั่วไปที่ไม่เกี่ยวกับ dh-task\n\n"
        "ถ้าผู้ใช้ถามเรื่องทั่วไปที่ต้องใช้ข้อมูลปัจจุบันจากอินเทอร์เน็ต (ข่าว, ราคา, สภาพอากาศ, เหตุการณ์ล่าสุด ฯลฯ) "
        "คุณมีเครื่องมือค้นเว็บ (Google Search) ให้ใช้ได้เลย ไม่ต้องตอบจากความจำเก่าหรือปฏิเสธว่าไม่รู้\n\n"
        "ตอบเป็นภาษาไทยเสมอ สุภาพ เป็นมิตร "
        "ข้อมูลที่ดึงมาจาก tool จะถูกแสดงเป็นการ์ด Flex Message แยกต่างหากให้ผู้ใช้ดูอยู่แล้ว "
        "ดังนั้นข้อความของคุณควรเป็นแค่ประโยคสรุปสั้นๆ 1-2 บรรทัด ไม่ต้องพิมพ์รายละเอียดตัวเลข/ชื่อ/ID ซ้ำ"
    )

    try:
        if _looks_like_data_question(user_message):
            print("🔒 forcing tool call (message matched a data-query keyword)")
            text = _forced_tool_turn(user_message, system_instruction, run_klive_command)
        else:
            # NOTE: Gemini's API rejects mixing a custom function tool and the
            # built-in google_search tool as two separate Tool entries. This
            # branch only runs for messages that already failed the
            # data-query keyword check, so it doesn't need run_klive_command
            # — only google_search.
            chat = gemini_client.chats.create(
                model=config.GEMINI_MODEL,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    system_instruction=system_instruction,
                ),
            )
            response = chat.send_message(user_message)
            text = response.text
    except Exception as e:
        if _is_quota_error(e):
            print(f"⚠️ Gemini quota/rate-limit hit: {e}")
            return {"text": _QUOTA_FALLBACK_TEXT, "flex": None}
        return {"text": f"ขออภัยครับ เกิดข้อผิดพลาดทางเทคนิค: {str(e)}", "flex": None}

    if "confirm_pending" in captured:
        # A destructive action was resolved and held for confirmation —
        # discard whatever the (forced) second Gemini call said about the
        # placeholder tool result, since the real answer here is the
        # confirm/cancel prompt the caller builds from this.
        return {"confirm_pending": captured["confirm_pending"]}

    flex = None
    if "data" in captured:
        try:
            flex = flex_builder.build_flex_for(
                captured["kind"], captured["data"], resolve_user=klive_service.resolve_user_name
            )
            if flex is None:
                print(f"⚠️ build_flex_for returned None for kind={captured.get('kind')!r} "
                      f"(unmapped subcommand or empty result) — data preview: {str(captured.get('data'))[:200]!r}")
        except Exception as e:
            print(f"⚠️ Flex build error for kind={captured.get('kind')}: {e}")
    else:
        print("ℹ️ No tool call captured this turn — Gemini answered without calling run_klive_command, so no Flex Message will be attached.")

    return {"text": text, "flex": flex}


async def get_gemini_response(user_message: str, user_id: str) -> dict:
    """Runs the blocking Gemini call in a worker thread so it never blocks
    the FastAPI event loop while waiting on the network. user_id is needed
    to attribute any destructive action (k-delete/k-update/etc.) held for
    confirmation to the right person."""
    import asyncio
    if config.LLM_PROVIDER == "deepseek":
        return await asyncio.to_thread(_ask_deepseek_sync, user_message, user_id)
    return await asyncio.to_thread(_ask_gemini_sync, user_message, user_id)


def _parse_reminder_sync(user_message: str) -> dict | None:
    """
    Turns free-form Thai/English text like "พรุ่งนี้ 9 โมงเช้า ประชุมทีม" into
    {"message": "ประชุมทีม", "due_at_iso": "2026-07-14T09:00:00+07:00"} by
    forcing exactly one call to a `create_reminder` tool — same forced-tool
    trick as run_klive_command, except here we want the tool's *arguments*
    (Gemini's parse of the date/time), not a natural-language reply.
    Returns None if Gemini didn't call the tool (message wasn't parseable
    as "remind me to do X at time Y") or on any error.
    """
    if config.LLM_PROVIDER != "gemini" or not gemini_client:
        return None

    def create_reminder(message: str, due_at_iso: str) -> str:
        """
        Schedules a reminder.

        Args:
            message: The short reminder text itself (what to be reminded about),
                with any date/time phrase stripped out.
            due_at_iso: The absolute due date+time in ISO 8601 format with the
                Asia/Bangkok UTC+07:00 offset, e.g. "2026-07-14T09:00:00+07:00".
                Resolve any relative/natural phrase (พรุ่งนี้, บ่ายสาม, next Monday,
                in 2 hours, etc.) against the current date/time given below.
        """
        return "ok"

    system_instruction = (
        "คุณคือตัวช่วยแยกวิเคราะห์คำขอตั้งเตือนความจำ\n"
        f"วันเวลาปัจจุบันคือ {_current_thai_datetime_str()}\n"
        "ผู้ใช้จะพิมพ์ข้อความที่มีทั้งเนื้อหาที่ต้องการให้เตือน และวัน/เวลาที่ต้องการให้เตือน "
        "(อาจเป็นภาษาพูด เช่น 'พรุ่งนี้เช้า', 'อีก 2 ชั่วโมง', 'ศุกร์นี้บ่ายสาม') "
        "ให้เรียก create_reminder เพียงครั้งเดียวเสมอ โดยแยกข้อความเตือนกับเวลาที่คำนวณแล้วออกจากกัน "
        "ถ้าข้อความไม่ได้ระบุเวลาไว้เลย ให้เดาว่าหมายถึงอีก 1 ชั่วโมงจากตอนนี้"
    )

    forced_config = types.GenerateContentConfig(
        tools=[create_reminder],
        system_instruction=system_instruction,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.ANY,
            )
        ),
    )
    user_content = types.Content(role="user", parts=[types.Part.from_text(text=user_message)])

    try:
        response = gemini_client.models.generate_content(
            model=config.GEMINI_MODEL, contents=[user_content], config=forced_config,
        )
        part = response.candidates[0].content.parts[0]
        fc = getattr(part, "function_call", None)
        if not fc:
            return None
        args = dict(fc.args or {})
        if not args.get("message") or not args.get("due_at_iso"):
            return None
        return {"message": args["message"], "due_at_iso": args["due_at_iso"]}
    except Exception as e:
        if _is_quota_error(e):
            print(f"⚠️ Reminder parser quota/rate-limit hit: {e}")
            return None
        print(f"⚠️ parse_reminder_request error: {e}")
        return None


async def parse_reminder_request(user_message: str) -> dict | None:
    import asyncio
    return await asyncio.to_thread(_parse_reminder_sync, user_message)
