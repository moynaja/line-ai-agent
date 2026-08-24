"""
Firestore-backed reminders. Each reminder is a document in the `reminders`
collection: user_id, message, due_at (ISO 8601, Asia/Bangkok-aware), created_at,
fired (bool).

Due reminders are pushed by an external caller hitting the /cron/check-reminders
endpoint (app/main.py) on a schedule — see check_and_fire(). This is
deliberately NOT an in-process scheduler (e.g. APScheduler), because Render's
free tier spins the service down after ~15 minutes of inactivity; an
in-process timer would simply stop running while asleep. An external cron
hitting the endpoint both fires due reminders AND keeps the service warm.
"""
import datetime
import uuid
from zoneinfo import ZoneInfo

from app.services import access_service

_memory_reminders: dict[str, list[dict]] = {}

REMINDERS_COLLECTION = "reminders"
BKK = ZoneInfo("Asia/Bangkok")


def _collection():
    client = access_service._get_client()
    if client is None:
        return None
    return client.collection(REMINDERS_COLLECTION)


def add_reminder(user_id: str, message: str, due_at: datetime.datetime) -> dict:
    reminder = {
        "user_id": user_id,
        "message": message,
        "due_at": due_at.astimezone(BKK).isoformat(),
        "created_at": datetime.datetime.now(BKK).isoformat(),
        "fired": False,
    }
    coll = _collection()
    if coll is None:
        reminder["id"] = str(uuid.uuid4())[:8]
        _memory_reminders.setdefault(user_id, []).append(reminder)
        return reminder
    doc_ref = coll.document()
    doc_ref.set(reminder)
    reminder["id"] = doc_ref.id
    return reminder


def list_upcoming(user_id: str, limit: int = 20) -> list[dict]:
    coll = _collection()
    if coll is None:
        items = [r for r in _memory_reminders.get(user_id, []) if not r["fired"]]
        return sorted(items, key=lambda r: r["due_at"])[:limit]
    query = (
        coll.where("user_id", "==", user_id)
        .where("fired", "==", False)
        .order_by("due_at")
        .limit(limit)
    )
    results = []
    for snap in query.stream():
        data = snap.to_dict()
        data["id"] = snap.id
        results.append(data)
    return results


def delete_reminder(user_id: str, index: int) -> bool:
    """index is 1-based, matching the numbered list from list_upcoming."""
    reminders = list_upcoming(user_id, limit=100)
    if index < 1 or index > len(reminders):
        return False
    reminder_id = reminders[index - 1]["id"]
    coll = _collection()
    if coll is None:
        _memory_reminders[user_id] = [
            r for r in _memory_reminders.get(user_id, []) if r["id"] != reminder_id
        ]
        return True
    coll.document(reminder_id).delete()
    return True


def get_due_reminders(now: datetime.datetime | None = None) -> list[dict]:
    """All not-yet-fired reminders across all users whose due_at has passed."""
    now = now or datetime.datetime.now(BKK)
    now_iso = now.astimezone(BKK).isoformat()
    coll = _collection()
    if coll is None:
        due = []
        for user_reminders in _memory_reminders.values():
            for r in user_reminders:
                if not r["fired"] and r["due_at"] <= now_iso:
                    due.append(r)
        return due
    query = coll.where("fired", "==", False).where("due_at", "<=", now_iso)
    results = []
    for snap in query.stream():
        data = snap.to_dict()
        data["id"] = snap.id
        results.append(data)
    return results


def mark_fired(reminder_id: str, user_id: str) -> None:
    coll = _collection()
    if coll is None:
        for r in _memory_reminders.get(user_id, []):
            if r["id"] == reminder_id:
                r["fired"] = True
        return
    coll.document(reminder_id).set({"fired": True}, merge=True)
