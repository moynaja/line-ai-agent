"""
Short-lived "are you sure?" holding area for destructive/risky dh-task
actions (k-delete, k-milestone-delete, k-update, k-milestone-update).

Gemini resolving a destructive tool call does NOT execute it immediately —
instead the resolved command_args are stashed here behind a random id, a
confirm/cancel Quick Reply is sent to the user, and the real klive command
only runs once the SAME user taps "confirm" within the expiry window.

Firestore-wise this is deliberately doc-get/set/delete only (no queries),
same reasoning as notes_service/reminder_service: avoids the composite-query
permission issues currently being chased down for this project's Firestore
setup, and a single random-id document lookup is all this needs anyway.

If Firestore isn't configured (or errors), falls back to an in-memory dict —
good enough for local dev / short-lived confirmations, though obviously
won't survive a restart or be shared across dynos on Render.
"""
import datetime
import uuid
from zoneinfo import ZoneInfo

from app.services import access_service

_memory_actions: dict[str, dict] = {}

PENDING_ACTIONS_COLLECTION = "pending_actions"
BKK = ZoneInfo("Asia/Bangkok")
EXPIRY_MINUTES = 5


def _collection():
    client = access_service._get_client()
    if client is None:
        return None
    return client.collection(PENDING_ACTIONS_COLLECTION)


def create_pending_action(user_id: str, command_args: list[str], summary_text: str) -> str:
    """Returns the new action_id to embed in the confirm/cancel postback data."""
    action_id = uuid.uuid4().hex[:12]
    now = datetime.datetime.now(BKK)
    record = {
        "user_id": user_id,
        "command_args": command_args,
        "summary_text": summary_text,
        "created_at": now.isoformat(),
        "expires_at": (now + datetime.timedelta(minutes=EXPIRY_MINUTES)).isoformat(),
    }
    coll = _collection()
    if coll is None:
        _memory_actions[action_id] = record
        return action_id
    coll.document(action_id).set(record)
    return action_id


def get_pending_action(action_id: str) -> dict | None:
    """Returns the record if it exists and hasn't expired yet, else None.
    Does NOT delete it — caller decides whether to delete on confirm/cancel."""
    coll = _collection()
    record = _memory_actions.get(action_id) if coll is None else None
    if coll is not None:
        snap = coll.document(action_id).get()
        record = snap.to_dict() if snap.exists else None
    if record is None:
        return None
    expires_at = datetime.datetime.fromisoformat(record["expires_at"])
    if datetime.datetime.now(BKK) > expires_at:
        return None
    return record


def delete_pending_action(action_id: str) -> None:
    coll = _collection()
    if coll is None:
        _memory_actions.pop(action_id, None)
        return
    coll.document(action_id).delete()
