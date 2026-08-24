"""
FastAPI entrypoint. Keeps only routing/wiring here — all real logic lives in
app/services and app/handlers.
"""
import sys

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import TextMessage

from app import config
from app.handlers.webhook_handler import process_webhook_events
from app.handlers import liff_handler
from app.services import access_service, dashboard_view, klive_service, line_service, reminder_service

if not config.LINE_CHANNEL_SECRET or not config.LINE_CHANNEL_ACCESS_TOKEN:
    print("❌ Critical Error: LINE_CHANNEL_SECRET or LINE_CHANNEL_ACCESS_TOKEN is missing!")
    sys.exit(1)

parser = WebhookParser(config.LINE_CHANNEL_SECRET)

app = FastAPI(title="Greenman LINE Bot Server")

app.mount("/liff", StaticFiles(directory="liff", html=True), name="liff")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


class RegisterRequest(BaseModel):
    user_id: str
    display_name: str = ""


@app.get("/", response_class=HTMLResponse)
def index():
    return "<h1>🚀 Greenman LINE Bot Server is ONLINE</h1>"


@app.post("/webhook")
async def callback(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature header.")

    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        events = parser.parse(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature.")

    background_tasks.add_task(process_webhook_events, events)
    return "OK"


@app.post("/api/liff/register")
async def liff_register(payload: RegisterRequest):
    status = await liff_handler.register_user(payload.user_id, payload.display_name)
    return {"status": status}


@app.get("/api/liff/config")
def liff_config():
    return {"liff_id": config.LIFF_ID}


@app.get("/api/liff/project-config")
def liff_project_config():
    return {"liff_id": config.LIFF_PROJECT_ID}


def _is_approved(user_id: str) -> bool:
    """Same admin-bypass + fail-open-on-Firestore-error policy as
    webhook_handler._resolve_status, duplicated here rather than imported
    since that one is chat-reply-shaped (returns a status string meant to
    drive a LINE reply) and this call site just needs a yes/no gate for the
    dashboard API."""
    if config.ADMIN_LINE_USER_ID and user_id == config.ADMIN_LINE_USER_ID:
        return True
    try:
        return access_service.get_status(user_id) == "approved"
    except Exception as e:
        print(f"🔥 Firestore error in get_status({user_id!r}) from dashboard API, failing OPEN: {e}")
        return True


@app.get("/api/project-dashboard/{project_id}")
def project_dashboard_api(project_id: str, user_id: str = ""):
    """Backs the full-screen web dashboard (liff/project/index.html). Gated
    the same way as the Detail postback/button in webhook_handler — the page
    sends liff.getProfile().userId as ?user_id=..., so a link that leaks
    outside LINE (forwarded screenshot of the URL, etc.) still can't be
    opened by someone who isn't an approved bot user, since userId itself
    isn't something an outsider can forge without their own LINE login."""
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id.")
    if not _is_approved(user_id):
        raise HTTPException(status_code=403, detail="Not approved.")

    try:
        dashboard = klive_service.get_project_dashboard(project_id)
    except Exception as e:
        print(f"🔥 Error building project dashboard (web) for project_id={project_id!r}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch project dashboard.")

    if not dashboard:
        raise HTTPException(status_code=404, detail="Project not found.")

    return dashboard_view.build_dashboard_view(dashboard, resolve_user=klive_service.resolve_user_name)


@app.get("/cron/check-reminders")
async def check_reminders(token: str = ""):
    """
    Pushes any reminder whose due time has passed, then marks it fired.
    Meant to be hit every 1-5 minutes by a free external cron service (e.g.
    cron-job.org, UptimeRobot) — see CRON_SECRET in app/config.py for why.
    This also incidentally keeps the free Render instance warm.
    """
    if config.CRON_SECRET:
        if token != config.CRON_SECRET:
            raise HTTPException(status_code=403, detail="Invalid token.")
    else:
        print("⚠️ CRON_SECRET not set — /cron/check-reminders is unauthenticated.")

    try:
        due = reminder_service.get_due_reminders()
    except Exception as e:
        # Don't 500 the whole cron hit just because Firestore is having an
        # issue — this endpoint is also the keep-alive ping, so it should
        # still return 200 even when reminders themselves can't be checked.
        print(f"🔥 Firestore error in get_due_reminders(): {e}")
        return {"fired": 0, "error": str(e)}

    for r in due:
        await line_service.push(r["user_id"], [
            TextMessage(text=f"⏰ ถึงเวลาแล้วครับ!\n{r['message']}")
        ])
        reminder_service.mark_fired(r["id"], r["user_id"])
    return {"fired": len(due)}
