"""
Thin wrapper around the LINE Messaging API client: singleton setup, reply/push
helpers, and the two small pieces of UI this app needs outside of Flex
Messages — the "please verify" link prompt and the admin approve/deny
quick-reply buttons.
"""
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    PostbackAction,
    URIAction,
)

from app import config

_line_bot_api_instance = None


def get_line_bot_api() -> AsyncMessagingApi:
    global _line_bot_api_instance
    if _line_bot_api_instance is None:
        configuration = Configuration(access_token=config.LINE_CHANNEL_ACCESS_TOKEN)
        async_api_client = AsyncApiClient(configuration)
        _line_bot_api_instance = AsyncMessagingApi(async_api_client)
    return _line_bot_api_instance


async def reply(reply_token: str, messages: list) -> None:
    if not messages:
        return
    api = get_line_bot_api()
    try:
        await api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=messages[:5]))
    except Exception as e:
        print(f"⚠️ Error replying to LINE: {e}")


async def push(user_id: str, messages: list) -> None:
    if not messages:
        return
    api = get_line_bot_api()
    try:
        await api.push_message(PushMessageRequest(to=user_id, messages=messages[:5]))
    except Exception as e:
        print(f"⚠️ Error pushing LINE message to {user_id}: {e}")


def build_verify_prompt(liff_url: str) -> TextMessage:
    """Sent to a first-time user: a tappable link that opens the LIFF
    verification page inside LINE."""
    return TextMessage(
        text=(
            "สวัสดีครับ ผม Greenman 🤖\n"
            "ก่อนเริ่มใช้งาน กรุณายืนยันตัวตนก่อนนะครับ กดลิงก์ด้านล่างได้เลย "
            "แล้วรอแอดมินอนุมัติอีกครั้งครับ"
        ),
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=URIAction(label="ยืนยันตัวตน", uri=liff_url))
        ]),
    )


def build_pending_notice() -> TextMessage:
    return TextMessage(text="คำขอของคุณกำลังรอแอดมินอนุมัติอยู่ครับ กรุณารอสักครู่นะครับ 🙏")


def build_denied_notice() -> TextMessage:
    return TextMessage(text="ขออภัยครับ คำขอใช้งานของคุณไม่ได้รับการอนุมัติ กรุณาติดต่อแอดมินโดยตรงครับ")


_MODE_INTRO = {
    "task": "📋 โหมดจัดการงาน (dh-task) — พิมพ์คุยได้เลยครับ เช่น 'งานของฉันมีอะไรบ้าง', 'สร้างงานใหม่ชื่อ...'",
    "chat": "💬 โหมดทั่วไป — ถามอะไรก็ได้ครับ พูดคุย ค้นข้อมูล ฯลฯ",
    "note": (
        "📝 โหมดบันทึก — พิมพ์อะไรก็ได้ ผมจะบันทึกให้ทันที\n"
        "พิมพ์ 'รายการ' เพื่อดูบันทึกทั้งหมด หรือ 'ลบ <หมายเลข>' เพื่อลบ"
    ),
    "remind": (
        "⏰ โหมดแจ้งเตือน — พิมพ์สิ่งที่อยากให้เตือนพร้อมเวลา เช่น 'พรุ่งนี้ 9 โมงเช้า ประชุมทีม'\n"
        "พิมพ์ 'รายการ' เพื่อดูรายการเตือนที่ตั้งไว้ หรือ 'ลบ <หมายเลข>' เพื่อลบ"
    ),
}


def build_mode_switch_notice(mode: str) -> TextMessage:
    return TextMessage(text=_MODE_INTRO.get(mode, "เปลี่ยนโหมดเรียบร้อยครับ"))


def build_notes_list(notes: list[dict]) -> TextMessage:
    if not notes:
        return TextMessage(text="ยังไม่มีบันทึกครับ ลองพิมพ์อะไรก็ได้เพื่อบันทึกดูครับ")
    lines = [f"{i}. {n['text']}" for i, n in enumerate(notes, start=1)]
    return TextMessage(text="📝 บันทึกของคุณ:\n" + "\n".join(lines))


def build_reminders_list(reminders: list[dict]) -> TextMessage:
    if not reminders:
        return TextMessage(text="ยังไม่มีรายการแจ้งเตือนครับ")
    lines = []
    for i, r in enumerate(reminders, start=1):
        due = r["due_at"][:16].replace("T", " ")
        lines.append(f"{i}. {r['message']} — {due}")
    return TextMessage(text="⏰ รายการแจ้งเตือน:\n" + "\n".join(lines))


def build_confirm_prompt(action_id: str, summary_text: str) -> TextMessage:
    """Sent before a destructive dh-task action (k-delete/k-update/etc.)
    actually runs — nothing executes until the user taps ยืนยัน."""
    return TextMessage(
        text=summary_text,
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(
                label="✅ ยืนยัน", data=f"do=confirm&id={action_id}", display_text="ยืนยัน"
            )),
            QuickReplyItem(action=PostbackAction(
                label="❌ ยกเลิก", data=f"do=cancel&id={action_id}", display_text="ยกเลิก"
            )),
        ]),
    )


def build_admin_approval_request(user_id: str, display_name: str) -> TextMessage:
    """Sent to the admin when a new user registers via the LIFF page."""
    return TextMessage(
        text=f"📝 มีคำขอใช้งานบอทใหม่\nชื่อ: {display_name or 'ไม่ทราบชื่อ'}\nต้องการอนุมัติหรือไม่ครับ?",
        quick_reply=QuickReply(items=[
            QuickReplyItem(action=PostbackAction(
                label="✅ อนุมัติ", data=f"action=approve&user_id={user_id}", display_text="อนุมัติ"
            )),
            QuickReplyItem(action=PostbackAction(
                label="❌ ปฏิเสธ", data=f"action=deny&user_id={user_id}", display_text="ปฏิเสธ"
            )),
        ]),
    )
