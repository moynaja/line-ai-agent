"""
Backend side of the LIFF verification page: takes the LINE profile the page
collected via liff.getProfile(), registers a 'pending' record, and — only on
the very first registration — notifies the admin so they can approve/deny.
"""
from app import config
from app.services import access_service, line_service


async def register_user(user_id: str, display_name: str) -> str:
    """Returns the resulting status ('pending' | 'approved' | 'denied')."""
    previous_status = access_service.get_status(user_id)
    status = access_service.register_pending(user_id, display_name)

    if previous_status is None and status == "pending" and config.ADMIN_LINE_USER_ID:
        await line_service.push(
            config.ADMIN_LINE_USER_ID,
            [line_service.build_admin_approval_request(user_id, display_name)],
        )
    return status
