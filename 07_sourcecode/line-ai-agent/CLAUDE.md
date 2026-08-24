# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Greenman" — a LINE Official Account bot (FastAPI webhook server) that uses Gemini AI function-calling to
let approved users manage tasks/projects/milestones in **dh-task** (internal project management system,
`https://tasks.dohome.technology`) by chatting or tapping a Rich Menu in LINE. Deployed on Render's free
tier. User state (approval status, current Rich Menu mode, notes, reminders, pending destructive-action
confirmations) is persisted in Firestore.

## Commands

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload   # local dev; main.py is a thin shim, real app is app/main.py
```

There is no test suite in this repo. The de facto verification workflow used throughout this project's
history (and expected for any change to `flex_builder.py` or `gemini_service.py`) is:

```bash
python3 -m py_compile <changed files>                       # syntax check
python3 -c "from linebot.v3.messaging import FlexContainer; FlexContainer.from_dict(payload)"   # validate Flex JSON against the real SDK schema
python3 -c "from google.genai import types; types.FunctionDeclaration.from_callable(client=..., callable=run_klive_command)"  # validate Gemini tool schema
```

Deployment is `git push` to `main` — Render auto-deploys (see `render.yaml`). Claude does not have push
credentials in this environment; after committing, the user must push and redeploy themselves.

## Architecture

```
LINE ──Webhook POST /webhook──▶ app/main.py ──▶ app/handlers/webhook_handler.py
                                                        │
                        ┌───────────────┬───────────────┼────────────────┐
                        ▼               ▼               ▼                ▼
                 app/services/*   gemini_service.py  klive_service.py  flex_builder.py
                 (Firestore-backed                  (subprocess wraps  (pure formatting:
                  state: access,                      tools/klive_tasks  JSON -> LINE Flex
                  mode, notes,                        _api.py, the      Message dicts)
                  reminders,                           official dh-task
                  pending_actions)                     CLI)
```

- **`app/main.py`** — FastAPI app. `main.py` at repo root is only a compatibility shim (`from app.main import app`) so `uvicorn main:app` keeps working; all real routes live in `app/main.py`.
- **`app/handlers/webhook_handler.py`** — routes every LINE event. Text messages are gated by `access_service` (unapproved users get a LIFF verify link instead of reaching Gemini), then routed by the sender's current Rich Menu mode (`mode_service`): `note`/`remind` go to dedicated handlers below; `task`/`chat` go to Gemini. Postback events are Rich Menu taps (`mode=...`), admin approve/deny buttons, or destructive-action confirm/cancel.
- **Rich Menu taps are postbacks, not text messages** (`scripts/setup_richmenu.sh` binds each area to `{"type": "postback", "data": "mode=task", "displayText": "งาน"}`). The `displayText` makes it *look* like the user typed "งาน" in the chat, but the webhook only ever receives a `PostbackEvent` — it never reaches `_handle_text_message`. Any behavior meant to trigger on a Rich Menu tap must be wired into `_handle_mode_postback`, not the text-message path; conflating the two was a real bug in this project's history.
- **`gemini_service.py`** — one big function (`run_klive_command`) whose **docstring** is introspected by the `google-genai` SDK (`types.FunctionDeclaration.from_callable`) to build the tool schema Gemini sees. The docstring is assembled from `docs/klive-tasks-SKILL.md` (the dh-task team's own CLI reference doc, loaded verbatim at import time) plus any custom virtual subcommands appended in code (e.g. `k-my-projects`, which has no real CLI equivalent — it's a deterministic Python filter, not something to leave to the model). Because free-form prompting turned out to unreliably skip tool calls, `_looks_like_data_question()` keyword-gates messages and `_forced_tool_turn()` forces exactly one tool call before letting the model produce natural language — see that function's docstring for why `tool_config=ANY` can't just be set on a normal chat session.
- **Destructive dh-task actions** (`k-delete`, `k-update`, `k-milestone-delete`, `k-milestone-update`) are intercepted inside `run_klive_command` before they run: resolved args are stashed in `pending_action_service` behind a random id, a confirm/cancel Quick Reply is sent, and the real command only executes if the *same* user taps confirm within 5 minutes.
- **`klive_service.py`** wraps `tools/klive_tasks_api.py` (the dh-task team's official CLI, bundled in-repo) as a subprocess, plus caches for user-id→name resolution and "self" identity resolution (`resolve_self_user_id()`, keyed off `SELF_EMAIL`/`config.SELF_EMAIL`). `PM_ROLE_ID` here is a **hardcoded, reverse-engineered** value — dh-task's `member_roles` field on a project is `{user_id: [role_id, ...]}` with no reference endpoint that maps role_id → role name, so this was derived by cross-referencing real production data against a known fact (the account is PM on exactly 7 projects).
- **`tools/klive_tasks_api.py`'s `cmd_users()` has a real bug**: it checks `if args.raw: dump everything; return` *before* applying `--search`, so `k-users --search <x> --raw` silently ignores `--search` and returns the full unfiltered user list. `resolve_self_user_id()` must never combine `--search` with `--raw` because of this — it fetches the full `k-users --raw` list and filters by email in Python instead. This was a real, confirmed production bug (self-identity silently resolved to the wrong dh-task account, so "my tasks"/"my projects" queries checked against someone else's `user_id`) — don't reintroduce the `--search --raw` combo for any user-lookup code path.
- **`flex_builder.py`** — pure functions, no I/O. Turns dh-task JSON into LINE Flex Message dicts (colored header bands per status, progress bars, nested milestone mini-cards under project bubbles). Always validate changes here against the real SDK (`FlexContainer.from_dict`) before considering them done — LINE's Flex schema has silent gotchas (e.g. 8-digit alpha-channel hex colors aren't confirmed-supported; stick to opaque 6-digit hex).
- **Firestore fail-open, everywhere, deliberately**: every Firestore read/write in `app/services/*` is wrapped so an error (there's an ongoing, still-unresolved `403 Missing or insufficient permissions` IAM issue on this project) degrades gracefully (treat as approved / default mode / skip persistence) rather than crashing the whole webhook reply. When adding new Firestore calls, follow this pattern — a bare unwrapped call was the root cause of a real production bug (every Rich Menu tap replying with a generic error) because the *write* path wasn't wrapped even though the *read* path was.
- **This dev sandbox has no outbound internet access** to `tasks.dohome.technology` (confirmed for both `curl` and Python `urllib`/`requests`) — only the deployed Render service can reach it. To inspect real dh-task API responses from this environment, use the pattern established in `app/main.py`: a temporary, token-gated debug endpoint (`/debug/klive-raw`, gated by `CRON_SECRET`) that the already-deployed service exposes, fetched via a tool that *does* have real internet access. Remove any such temporary endpoint once it's served its purpose.
- Render free tier spins the service down after ~15 min idle (30-50s+ cold start). `/cron/check-reminders` doubles as both the reminders-firing cron and a keep-alive ping (hit every 1-5 min by an external cron service like cron-job.org, gated by `CRON_SECRET`).

## dh-task / klive-tasks integration reference

- Canonical skill/reference page for the dh-task CLI (all supported agent integrations — Claude Code, Codex, Cursor, Kiro, Windsurf, Antigravity, Hermes): `https://tasks.dohome.technology/skills`. `docs/klive-tasks-SKILL.md` in this repo is a copy of that skill's `SKILL.md` and is the source of truth `gemini_service.py` loads its tool description from — if the dh-task team updates their skill definition, re-fetch and replace that file rather than hand-editing it (custom additions like `k-my-projects` are appended separately in `gemini_service.py`, not written into that file).
- Self-identity: the bot resolves "ผม/ฉัน/ของฉัน/ตัวเอง" to one specific dh-task account via `SELF_EMAIL` (`app/config.py`, default `wirun.pin@dohome.co.th` — the project owner's dh-task login). This is used both as the `--assignee` value for "my tasks" queries and as the identity checked against `member_roles`/`PM_ROLE_ID` for "my projects" queries.
- The project owner's raw dh-task `user_id` (what `resolve_self_user_id()` resolves `SELF_EMAIL` to, and the key checked against each project's `member_roles` dict) is `6a1eb6950110e0b0c39f492f`. Confirmed via real `k-users` data: this id's `last_name` field is literally `"PM"`.
