"""
Firestore-backed user registry for the admin-approval access gate.

Flow: a brand-new LINE user is sent a LIFF verification link. Opening it
registers them as "pending" here. The admin gets a push message with
Approve/Deny quick-reply buttons; tapping one calls approve()/deny(), which
is what actually lets (or keeps blocking) the bot from responding to them.

If Firestore isn't configured (no GOOGLE_APPLICATION_CREDENTIALS set), this
fails open — everyone is treated as approved — so local development and any
environment that hasn't set up Firestore yet still behaves like before this
feature existed, rather than silently locking everyone out.
"""
import datetime

from app import config

_client = None
_firestore_ready = False


def _get_client():
    """Lazily creates the Firestore client. Returns None if not configured."""
    global _client, _firestore_ready
    if _firestore_ready:
        return _client
    _firestore_ready = True
    if not config.GOOGLE_APPLICATION_CREDENTIALS:
        print("⚠️ GOOGLE_APPLICATION_CREDENTIALS not set — access control is DISABLED "
              "(everyone is treated as approved) until Firestore is configured.")
        return None
    try:
        from google.cloud import firestore
        _client = firestore.Client.from_service_account_json(
            config.GOOGLE_APPLICATION_CREDENTIALS,
            project=config.FIRESTORE_PROJECT_ID or None,
        )
        print("✅ Firestore access-control client ready.")
    except Exception as e:
        print(f"⚠️ Could not initialize Firestore client, access control is DISABLED: {e}")
        _client = None
    return _client


def _doc(user_id: str):
    client = _get_client()
    if client is None:
        return None
    return client.collection(config.FIRESTORE_COLLECTION).document(user_id)


def get_status(user_id: str) -> str | None:
    """Returns 'approved' | 'pending' | 'denied' | None (never registered).
    Returns 'approved' unconditionally if Firestore isn't configured (fail-open)."""
    doc_ref = _doc(user_id)
    if doc_ref is None:
        return "approved"
    snap = doc_ref.get()
    if not snap.exists:
        return None
    return snap.to_dict().get("status")


def is_approved(user_id: str) -> bool:
    return get_status(user_id) == "approved"


def register_pending(user_id: str, display_name: str = "") -> str:
    """Creates a 'pending' record if this user has never been seen before.
    If they already have a record (approved/pending/denied), leaves it
    untouched. Returns the resulting status."""
    doc_ref = _doc(user_id)
    if doc_ref is None:
        return "approved"
    snap = doc_ref.get()
    if snap.exists:
        return snap.to_dict().get("status")
    doc_ref.set({
        "status": "pending",
        "display_name": display_name,
        "requested_at": datetime.datetime.utcnow().isoformat(),
    })
    return "pending"


def approve(user_id: str) -> None:
    doc_ref = _doc(user_id)
    if doc_ref is None:
        return
    doc_ref.set({
        "status": "approved",
        "decided_at": datetime.datetime.utcnow().isoformat(),
    }, merge=True)


def deny(user_id: str) -> None:
    doc_ref = _doc(user_id)
    if doc_ref is None:
        return
    doc_ref.set({
        "status": "denied",
        "decided_at": datetime.datetime.utcnow().isoformat(),
    }, merge=True)


def get_display_name(user_id: str) -> str:
    doc_ref = _doc(user_id)
    if doc_ref is None:
        return ""
    snap = doc_ref.get()
    if not snap.exists:
        return ""
    return snap.to_dict().get("display_name", "")
