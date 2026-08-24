"""
Firestore-backed personal notes ("บันทึก"). Each note is a document in the
`notes` collection with fields: user_id, text, created_at (ISO string).

If Firestore isn't configured, notes are kept in an in-memory list per
process — fine for local dev/testing, but they won't survive a restart and
won't be shared across dynos. This mirrors the fail-open-ish behavior of
access_service/mode_service so the bot never crashes just because Firestore
isn't set up yet.
"""
import datetime
import uuid

from app.services import access_service

_memory_notes: dict[str, list[dict]] = {}

NOTES_COLLECTION = "notes"


def _collection():
    client = access_service._get_client()
    if client is None:
        return None
    return client.collection(NOTES_COLLECTION)


def add_note(user_id: str, text: str) -> dict:
    note = {
        "user_id": user_id,
        "text": text,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    coll = _collection()
    if coll is None:
        note["id"] = str(uuid.uuid4())[:8]
        _memory_notes.setdefault(user_id, []).append(note)
        return note
    doc_ref = coll.document()
    doc_ref.set(note)
    note["id"] = doc_ref.id
    return note


def list_notes(user_id: str, limit: int = 20) -> list[dict]:
    coll = _collection()
    if coll is None:
        return list(reversed(_memory_notes.get(user_id, [])))[:limit]
    query = (
        coll.where("user_id", "==", user_id)
        .order_by("created_at", direction="DESCENDING")
        .limit(limit)
    )
    results = []
    for snap in query.stream():
        data = snap.to_dict()
        data["id"] = snap.id
        results.append(data)
    return results


def delete_note(user_id: str, index: int) -> bool:
    """index is 1-based, matching the numbered list shown to the user
    (as returned by list_notes, newest first)."""
    notes = list_notes(user_id, limit=100)
    if index < 1 or index > len(notes):
        return False
    note_id = notes[index - 1]["id"]
    coll = _collection()
    if coll is None:
        _memory_notes[user_id] = [n for n in _memory_notes.get(user_id, []) if n["id"] != note_id]
        return True
    coll.document(note_id).delete()
    return True
