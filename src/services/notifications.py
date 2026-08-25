"""Push notification triggers on application status changes."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def notify_application_status_change(
    application: dict[str, Any],
    new_status: str,
    resident_name: str,
    checklist_item_name: str,
) -> None:
    """Send push notification when application status changes.

    Fails silently if push service is unavailable — status update is still
    committed, notification failure should not roll back the administrative action.
    """
    user_id = application["user_id"]

    status_messages: dict[str, tuple[str, str]] = {
        "received": (
            "Hồ sơ đã được gửi",
            f"Hồ sơ đăng ký {checklist_item_name} đang chờ BQL xử lý.",
        ),
        "processing": (
            "Hồ sơ đang được xử lý",
            "Hồ sơ của bạn đang được BQL xem xét.",
        ),
        "needs_info": (
            "Hồ sơ cần bổ sung giấy tờ",
            f"Vui lòng bổ sung giấy tờ cho hồ sơ {checklist_item_name}.",
        ),
        "approved": (
            "Hồ sơ đã được duyệt!",
            f"Chúc mừng! Hồ sơ {checklist_item_name} đã được duyệt.",
        ),
        "rejected": (
            "Hồ sơ bị từ chối",
            f"Hồ sơ {checklist_item_name} không được duyệt."
            f" Lý do: {application.get('bql_note') or 'Không có ghi chú'}.",
        ),
    }

    if new_status not in status_messages:
        return

    title, body = status_messages[new_status]
    url = "/documents"

    try:
        # Lazy import to avoid circular dependency and allow testing without
        # the push service being configured.
        from src.services import push

        await push.send_push_to_user(user_id, title, body, url)
    except Exception:  # noqa: BLE001 — notification failure is non-fatal
        logger.exception("Failed to send push notification to user %s", user_id)


async def notify_bql_new_application(
    application: dict[str, Any],
    resident_name: str,
    checklist_item_name: str,
) -> None:
    """Notify BQL when a new application is submitted.

    Currently logs the notification. Full implementation requires a mechanism
    to route notifications to admin users (e.g., a separate admin push list
    or a dedicated admin notification channel).
    """
    title = "Có hồ sơ mới cần xử lý"
    body = f"Cư dân {resident_name} vừa nộp hồ sơ {checklist_item_name}."

    logger.info("BQL notification: %s - %s (application_id=%s)", title, body, application.get("application_id"))
