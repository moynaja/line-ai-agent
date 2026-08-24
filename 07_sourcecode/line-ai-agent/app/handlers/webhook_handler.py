"""
Routes incoming LINE webhook events:
  - Text messages from unapproved users get a verify-link / pending / denied
    reply instead of reaching Gemini.
  - Text messages from approved users are routed by their current Rich Menu
    mode (task/chat -> Gemini as before, note/remind -> the Notes/Reminders
    features below).
  - Postback events are either a Rich Menu tap (mode=task|chat|note|remind,
    switches the sender's mode) or the admin approving/denying a pending
    user via the quick-reply buttons sent to them (action=approve|deny).
"""
import datetime
import time
from zoneinfo import ZoneInfo

from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent
from linebot.v3.messaging import TextMessage, FlexMessage, FlexContainer

import flex_builder
from app import config
from app.services import (
    access_service, gemini_service, klive_service, line_service,
    mode_service, notes_service, pending_action_service, reminder_service,
)

BKK = ZoneInfo("Asia/Bangkok")
_LIST_WORDS = ("รายการ", "list")
_DELETE_WORDS = ("ลบ", "delete")

# Rich Menu / bare one-word shortcut for "which projects am I managing".
# Handled as a deterministic filter over member_roles (see
# klive_service.list_my_managed_projects), NOT expanded into a question for
# Gemini — matching a hardcoded PM role_id against raw JSON isn't something
# to leave to the model's judgment, and it also lets this skip the LLM
# round-trip entirely for a faster reply.
_PM_PROJECTS_TRIGGERS = {"งาน", "task", "tasks"}


def _liff_verify_url() -> str:
    if config.LIFF_ID:
        return f"https://liff.line.me/{config.LIFF_ID}"
    # Fallback so the bot doesn't crash before LIFF_ID is configured — this
    # obviously isn't a real LIFF link, it's just visible in logs/replies so
    # it's easy to notice the setup step hasn't been finished yet.
    return "https://example.com/liff-not-configured-yet"


def _resolve_status(user_id: str) -> str:
    """Same admin-bypass + Firestore lookup used for both text messages and
    Rich Menu postbacks, so a not-yet-approved user tapping the menu gets the
    same verify/pending/denied treatment as messaging directly.

    If Firestore itself errors out (e.g. a permissions misconfiguration),
    this fails OPEN rather than letting the exception propagate and leave
    the user with zero reply — same fail-open philosophy as when Firestore
    isn't configured at all, just extended to cover transient/misconfigured
    Firestore errors too. The error is still logged loudly so it's visible
    in Render logs."""
    is_admin = bool(config.ADMIN_LINE_USER_ID) and user_id == config.ADMIN_LINE_USER_ID
    if is_admin:
        return "approved"
    try:
        return access_service.get_status(user_id)
    except Exception as e:
        print(f"🔥 Firestore error in get_status({user_id!r}), failing OPEN (treating as approved): {e}")
        return "approved"


def _get_mode_safe(user_id: str) -> str:
    """Same fail-open reasoning as _resolve_status: a Firestore error here
    must not take down the whole message — fall back to default chat mode
    instead of raising."""
    try:
        return mode_service.get_mode(user_id)
    except Exception as e:
        print(f"🔥 Firestore error in get_mode({user_id!r}), defaulting to 'chat' mode: {e}")
        return mode_service.DEFAULT_MODE


async def _gate_reply(reply_token: str, user_id: str, status: str) -> None:
    if status is None:
        display_name = ""
        try:
            profile = await line_service.get_line_bot_api().get_profile(user_id)
            display_name = profile.display_name or ""
        except Exception as e:
            print(f"⚠️ Could not fetch profile for {user_id}: {e}")
        # We don't auto-register here — registration happens through the
        # LIFF page so we capture a real display name/profile via liff.getProfile().
        # This message just nudges them to open it.
        await line_service.reply(reply_token, [line_service.build_verify_prompt(_liff_verify_url())])
    elif status == "pending":
        await line_service.reply(reply_token, [line_service.build_pending_notice()])
    elif status == "denied":
        await line_service.reply(reply_token, [line_service.build_denied_notice()])


async def _handle_notes_mode(reply_token: str, user_id: str, user_message: str) -> None:
    stripped = user_message.strip()
    if stripped in _LIST_WORDS:
        notes = notes_service.list_notes(user_id)
        await line_service.reply(reply_token, [line_service.build_notes_list(notes)])
        return
    if any(stripped.startswith(w) for w in _DELETE_WORDS):
        digits = "".join(c for c in stripped if c.isdigit())
        if digits and notes_service.delete_note(user_id, int(digits)):
            await line_service.reply(reply_token, [TextMessage(text=f"ลบบันทึกที่ {digits} แล้วครับ ✅")])
        else:
            await line_service.reply(reply_token, [TextMessage(text="ไม่พบบันทึกที่ต้องการลบครับ ลองพิมพ์ 'รายการ' ดูเลขก่อนได้ครับ")])
        return
    notes_service.add_note(user_id, stripped)
    await line_service.reply(reply_token, [TextMessage(text="บันทึกแล้วครับ 📝")])


async def _handle_remind_mode(reply_token: str, user_id: str, user_message: str) -> None:
    stripped = user_message.strip()
    if stripped in _LIST_WORDS:
        reminders = reminder_service.list_upcoming(user_id)
        await line_service.reply(reply_token, [line_service.build_reminders_list(reminders)])
        return
    if any(stripped.startswith(w) for w in _DELETE_WORDS):
        digits = "".join(c for c in stripped if c.isdigit())
        if digits and reminder_service.delete_reminder(user_id, int(digits)):
            await line_service.reply(reply_token, [TextMessage(text=f"ลบรายการแจ้งเตือนที่ {digits} แล้วครับ ✅")])
        else:
            await line_service.reply(reply_token, [TextMessage(text="ไม่พบรายการแจ้งเตือนที่ต้องการลบครับ ลองพิมพ์ 'รายการ' ดูเลขก่อนได้ครับ")])
        return

    parsed = await gemini_service.parse_reminder_request(stripped)
    if not parsed:
        await line_service.reply(reply_token, [TextMessage(
            text="ขอโทษครับ ไม่เข้าใจเวลาที่ต้องการ ลองพิมพ์ใหม่ เช่น 'พรุ่งนี้ 9 โมงเช้า ประชุมทีม'"
        )])
        return
    try:
        due_at = datetime.datetime.fromisoformat(parsed["due_at_iso"])
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=BKK)
    except ValueError:
        await line_service.reply(reply_token, [TextMessage(text="ขอโทษครับ แปลงเวลาที่ต้องการไม่สำเร็จ ลองพิมพ์ใหม่อีกครั้งครับ")])
        return

    reminder_service.add_reminder(user_id, parsed["message"], due_at)
    due_str = due_at.strftime("%d/%m/%Y %H:%M")
    await line_service.reply(reply_token, [TextMessage(
        text=f"ตั้งเตือนแล้วครับ ⏰\n{parsed['message']}\nเวลา {due_str} น."
    )])


async def _handle_pm_projects(reply_token: str) -> None:
    """Rich Menu tap / '"งาน"' shortcut: shows the projects the user is PM of
    (per dh-task's member_roles field), each with its milestones nested
    inside. Bypasses Gemini entirely — see the _PM_PROJECTS_TRIGGERS comment."""
    try:
        projects = klive_service.list_my_managed_projects()
    except Exception as e:
        print(f"🔥 Error building PM project list: {e}")
        await line_service.reply(reply_token, [TextMessage(
            text="ขออภัยครับ ดึงข้อมูลโปรเจกต์ไม่สำเร็จ ลองใหม่อีกครั้งครับ"
        )])
        return

    if not projects:
        await line_service.reply(reply_token, [TextMessage(
            text="ไม่พบโปรเจกต์ที่คุณเป็น PM ครับ"
        )])
        return

    messages = [TextMessage(text=f"คุณเป็น PM อยู่ {len(projects)} โปรเจกต์ครับ 👇")]
    flex = flex_builder.build_flex_for("k-projects", projects, resolve_user=klive_service.resolve_user_name)
    if flex:
        try:
            container = FlexContainer.from_dict(flex["contents"])
            messages.append(FlexMessage(alt_text=flex["alt_text"], contents=container))
        except Exception as e:
            print(f"⚠️ Could not attach Flex Message, falling back to text only: {e}")

    await line_service.reply(reply_token, messages)


async def _handle_project_detail_postback(event: PostbackEvent, project_id: str) -> None:
    """"ดูรายละเอียดเพิ่มเติม" footer button on a project card (see
    flex_builder.build_project_bubble's show_detail_button) — fetches the
    fuller PM Dashboard view (klive_service.get_project_dashboard) and
    replies with it. Gated the same way as every other entry point so a
    not-yet-approved user tapping an old card doesn't reach dh-task data."""
    user_id = event.source.user_id
    status = _resolve_status(user_id)
    if status != "approved":
        await _gate_reply(event.reply_token, user_id, status)
        return

    try:
        dashboard = klive_service.get_project_dashboard(project_id)
    except Exception as e:
        print(f"🔥 Error building project dashboard for project_id={project_id!r}: {e}")
        await line_service.reply(event.reply_token, [TextMessage(
            text="ขออภัยครับ ดึงข้อมูลภาพรวมโปรเจกต์ไม่สำเร็จ ลองใหม่อีกครั้งครับ"
        )])
        return

    if not dashboard:
        await line_service.reply(event.reply_token, [TextMessage(text="ไม่พบข้อมูลโปรเจกต์นี้ครับ")])
        return

    messages = []
    try:
        flex = flex_builder.build_project_dashboard_message(dashboard, resolve_user=klive_service.resolve_user_name)
        container = FlexContainer.from_dict(flex["contents"])
        messages.append(FlexMessage(alt_text=flex["alt_text"], contents=container))
    except Exception as e:
        print(f"⚠️ Could not build/attach project dashboard Flex Message: {e}")
        messages.append(TextMessage(text="ขออภัยครับ สร้างการ์ดสรุปไม่สำเร็จ ลองใหม่อีกครั้งครับ"))

    await line_service.reply(event.reply_token, messages)


async def _handle_text_message(event: MessageEvent) -> None:
    user_id = event.source.user_id
    user_message = event.message.text
    reply_token = event.reply_token

    status = _resolve_status(user_id)
    print(f"👤 message from user_id={user_id} status={status!r}: {user_message!r}")

    if status != "approved":
        await _gate_reply(reply_token, user_id, status)
        return

    mode = _get_mode_safe(user_id)

    if mode == "note":
        try:
            await _handle_notes_mode(reply_token, user_id, user_message)
        except Exception as e:
            print(f"🔥 Error in notes mode for {user_id!r}: {e}")
            await line_service.reply(reply_token, [TextMessage(
                text="ขออภัยครับ ระบบบันทึกขัดข้องชั่วคราว ลองใหม่อีกครั้งครับ"
            )])
        return

    if mode == "remind":
        try:
            await _handle_remind_mode(reply_token, user_id, user_message)
        except Exception as e:
            print(f"🔥 Error in remind mode for {user_id!r}: {e}")
            await line_service.reply(reply_token, [TextMessage(
                text="ขออภัยครับ ระบบแจ้งเตือนขัดข้องชั่วคราว ลองใหม่อีกครั้งครับ"
            )])
        return

    # mode == "task" or "chat" (or unset/default) -> normal Gemini + Flex flow,
    # except the PM-projects shortcut below, which bypasses Gemini entirely.
    if user_message.strip().lower() in _PM_PROJECTS_TRIGGERS:
        print(f"✏️ {user_message!r} matched PM-projects shortcut — skipping Gemini")
        await _handle_pm_projects(reply_token)
        return

    t0 = time.time()
    result = await gemini_service.get_gemini_response(user_message, user_id)
    print(f"⏱️ get_gemini_response took {time.time() - t0:.2f}s for message: {user_message!r}")

    if result.get("confirm_pending"):
        # Gemini resolved a destructive action (k-delete/k-update/etc.) —
        # nothing has executed yet. Send the confirm/cancel Quick Reply;
        # the real command only runs if this same user taps ยืนยัน within
        # the 5-minute window (see _handle_confirm_postback).
        pending = result["confirm_pending"]
        await line_service.reply(reply_token, [
            line_service.build_confirm_prompt(pending["action_id"], pending["summary_text"])
        ])
        return

    messages = []
    if result.get("text"):
        messages.append(TextMessage(text=result["text"]))
    if result.get("flex"):
        try:
            container = FlexContainer.from_dict(result["flex"]["contents"])
            messages.append(FlexMessage(alt_text=result["flex"]["alt_text"], contents=container))
        except Exception as e:
            print(f"⚠️ Could not attach Flex Message, falling back to text only: {e}")
    if not messages:
        messages = [TextMessage(text="ขออภัยครับ ไม่พบข้อมูลที่จะตอบ")]

    await line_service.reply(reply_token, messages)


async def _handle_mode_postback(event: PostbackEvent, mode: str) -> None:
    """Handles a Rich Menu tap (mode=task|chat|note|remind), switching the
    sender's current mode. Gated the same way normal messages are, so a
    not-yet-approved user tapping the menu gets the verify/pending/denied
    reply instead of silently getting a mode set."""
    user_id = event.source.user_id
    status = _resolve_status(user_id)
    if status != "approved":
        await _gate_reply(event.reply_token, user_id, status)
        return
    try:
        mode_service.set_mode(user_id, mode)
    except Exception as e:
        # Same fail-open reasoning as _get_mode_safe: a Firestore error here
        # must not crash the whole postback (this was the actual cause of
        # the generic "เกิดข้อผิดพลาดทางเทคนิค" reply on every Rich Menu tap —
        # the write wasn't wrapped even though the read already was). Worst
        # case the mode switch doesn't persist and the next message falls
        # back to default mode; the user still gets a normal reply either way.
        print(f"🔥 Firestore error in set_mode({user_id!r}, {mode!r}), continuing anyway: {e}")

    if mode == "task":
        # Tapping the "งาน" Rich Menu button is bound to a postback
        # (data="mode=task", displayText="งาน" — see scripts/setup_richmenu.sh),
        # so it never reaches _handle_text_message / _PM_PROJECTS_TRIGGERS no
        # matter what that logic does. Show the PM-project list directly here
        # instead of the generic mode-switch notice — this is the actual
        # "tap and see results immediately" behavior the user asked for.
        await _handle_pm_projects(event.reply_token)
    else:
        await line_service.reply(event.reply_token, [line_service.build_mode_switch_notice(mode)])


async def _handle_confirm_postback(event: PostbackEvent, confirmed: bool, action_id: str) -> None:
    """Handles the ✅ ยืนยัน / ❌ ยกเลิก buttons on a destructive-action
    confirmation (k-delete/k-update/etc. — see gemini_service.DESTRUCTIVE_SUBCOMMANDS).
    Only the user who triggered the original request may confirm/cancel it,
    and it must still be within the 5-minute expiry window."""
    sender_id = event.source.user_id
    try:
        pending = pending_action_service.get_pending_action(action_id)
    except Exception as e:
        # Fail closed here (not open): if we can't verify the pending action
        # at all, we must not run a destructive command blind. Same Firestore
        # 403 class of bug as set_mode — treat it like "expired" rather than
        # letting the exception crash the postback into the generic fallback.
        print(f"🔥 Firestore error in get_pending_action({action_id!r}): {e}")
        pending = None

    if pending is None:
        await line_service.reply(event.reply_token, [TextMessage(
            text="คำขอนี้หมดอายุหรือถูกดำเนินการไปแล้วครับ กรุณาพิมพ์คำสั่งใหม่อีกครั้งเพื่อความปลอดภัย"
        )])
        return

    if pending["user_id"] != sender_id:
        print(f"⚠️ Ignoring confirm/cancel postback from {sender_id!r} for action owned by {pending['user_id']!r}")
        return

    try:
        pending_action_service.delete_pending_action(action_id)
    except Exception as e:
        print(f"🔥 Firestore error in delete_pending_action({action_id!r}), continuing anyway: {e}")

    if not confirmed:
        await line_service.reply(event.reply_token, [TextMessage(text="ยกเลิกแล้วครับ ไม่มีการเปลี่ยนแปลงข้อมูลใดๆ")])
        return

    output = klive_service.run_klive(pending["command_args"])
    print(f"🔨 confirmed destructive action executed: {pending['command_args']} -> {len(output)} chars")
    if output.lower().startswith("error"):
        await line_service.reply(event.reply_token, [TextMessage(
            text=f"ขออภัยครับ ดำเนินการไม่สำเร็จ: {output[:200]}"
        )])
    else:
        await line_service.reply(event.reply_token, [TextMessage(text="ดำเนินการเรียบร้อยแล้วครับ ✅")])


async def _handle_postback(event: PostbackEvent) -> None:
    """Handles the kinds of postback this bot sends:
      - Rich Menu taps (data="mode=task|chat|note|remind")
      - Admin Approve/Deny on a registration request (data="action=approve|deny&user_id=...")
      - Confirm/cancel on a destructive dh-task action (data="confirm_action&id=..." / "cancel_action&id=...")
      - "ดูรายละเอียดเพิ่มเติม" Detail button on a project card (data="view=project&id=...")
    """
    data = dict(pair.split("=", 1) for pair in event.postback.data.split("&") if "=" in pair)

    if "mode" in data:
        await _handle_mode_postback(event, data["mode"])
        return

    if data.get("do") in ("confirm", "cancel"):
        await _handle_confirm_postback(event, confirmed=data["do"] == "confirm", action_id=data.get("id", ""))
        return

    if data.get("view") == "project" and data.get("id"):
        await _handle_project_detail_postback(event, data["id"])
        return

    sender_id = event.source.user_id
    if not config.ADMIN_LINE_USER_ID or sender_id != config.ADMIN_LINE_USER_ID:
        print(f"⚠️ Ignoring postback from non-admin user_id={sender_id}")
        return

    action = data.get("action")
    target_user_id = data.get("user_id")
    if not target_user_id or action not in ("approve", "deny"):
        return

    if action == "approve":
        access_service.approve(target_user_id)
        await line_service.push(target_user_id, [
            TextMessage(text="คุณได้รับการอนุมัติให้ใช้งานบอทแล้วครับ ✅ ลองทักมาใหม่ได้เลยครับ")
        ])
        await line_service.reply(event.reply_token, [TextMessage(text="อนุมัติเรียบร้อยครับ ✅")])
    else:
        access_service.deny(target_user_id)
        await line_service.push(target_user_id, [
            TextMessage(text="ขออภัยครับ คำขอใช้งานของคุณไม่ได้รับการอนุมัติ")
        ])
        await line_service.reply(event.reply_token, [TextMessage(text="ปฏิเสธคำขอเรียบร้อยครับ ❌")])


async def process_webhook_events(events: list) -> None:
    for event in events:
        try:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                await _handle_text_message(event)
            elif isinstance(event, PostbackEvent):
                await _handle_postback(event)
        except Exception as e:
            import traceback
            print(f"⚠️ Error handling event: {e}")
            traceback.print_exc()
            # Last-resort safety net: an unhandled exception anywhere above
            # must not leave the user with total silence. Best-effort only —
            # the reply_token may already be used/expired in some cases.
            reply_token = getattr(event, "reply_token", None)
            if reply_token:
                try:
                    await line_service.reply(reply_token, [TextMessage(
                        text="ขออภัยครับ เกิดข้อผิดพลาดทางเทคนิค ลองใหม่อีกครั้งครับ 🙏"
                    )])
                except Exception as reply_error:
                    print(f"⚠️ Also failed to send fallback error reply: {reply_error}")
