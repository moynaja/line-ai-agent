"""
Tracks which "mode" each LINE user is currently in (task / chat / note /
remind), set by tapping the Rich Menu. Text messages sent afterwards are
routed based on this until the user taps a different Rich Menu button.

Backed by the same Firestore project as access_service (bot_users collection,
one doc per user_id) so no extra setup is needed. Falls back to a
plain in-memory dict if Firestore isn't configured — good enough for local
dev, though it obviously won't survive a restart/across dynos.
"""
from app import config
from app.services import access_service

_memory_modes: dict[str, str] = {}

DEFAULT_MODE = "chat"
VALID_MODES = ("task", "chat", "note", "remind")


def get_mode(user_id: str) -> str:
    doc_ref = access_service._doc(user_id)  # reuses the same Firestore client/doc
    if doc_ref is None:
        return _memory_modes.get(user_id, DEFAULT_MODE)
    snap = doc_ref.get()
    if not snap.exists:
        return DEFAULT_MODE
    return snap.to_dict().get("current_mode", DEFAULT_MODE)


def set_mode(user_id: str, mode: str) -> None:
    if mode not in VALID_MODES:
        return
    doc_ref = access_service._doc(user_id)
    if doc_ref is None:
        _memory_modes[user_id] = mode
        return
    doc_ref.set({"current_mode": mode}, merge=True)
