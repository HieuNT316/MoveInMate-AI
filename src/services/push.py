"""Web Push notification service.

VAPID keys MUST be configured in .env. Private key never logged.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import httpx

from src.config import get_settings

if TYPE_CHECKING:
    from webpush import WebPush

logger = logging.getLogger(__name__)

# Lazy import: web-push is optional, only needed when actually sending.
_webpush: type | None = None


def _get_webpush() -> type | None:
    global _webpush
    if _webpush is None:
        try:
            from webpush import WebPush as wp_module  # noqa: N813
            _webpush = wp_module
        except ImportError:
            _webpush = False
    return _webpush if _webpush else None


class PushError(Exception):
    """Push notification failed."""
    pass


class SubscriptionExpired(PushError):  # noqa: N818
    """Subscription no longer valid."""
    pass


def _init_webpush() -> WebPush | None:
    """Initialize web-push with VAPID keys."""
    settings = get_settings()
    if not settings.has_vapid_keys:
        logger.warning("VAPID keys not configured, push disabled")
        return None

    webpush_cls = _get_webpush()
    if webpush_cls is None:
        logger.warning("web-push library not installed, push disabled")
        return None

    return webpush_cls(
        public_key=settings.vapid_public_key,
        private_key=settings.vapid_private_key,
        subscriber_email=settings.vapid_subject,
    )


def upsert_push_subscription(
    db: Any,
    user_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Upsert push subscription by endpoint."""
    from sqlalchemy import text

    stmt = text("""
        INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth, user_agent, updated_at)
        VALUES (:user_id, :endpoint, :p256dh, :auth, :user_agent, NOW())
        ON CONFLICT (endpoint) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            p256dh = EXCLUDED.p256dh,
            auth = EXCLUDED.auth,
            user_agent = EXCLUDED.user_agent,
            updated_at = NOW()
        RETURNING subscription_id
    """)
    result = db.execute(stmt, {
        "user_id": user_id,
        "endpoint": endpoint,
        "p256dh": p256dh,
        "auth": auth,
        "user_agent": user_agent,
    })
    db.commit()
    return {"subscription_id": result.scalar()}


def delete_push_subscription(db: Any, user_id: int, endpoint: str) -> bool:
    """Delete push subscription (only if owned by user)."""
    from sqlalchemy import text

    stmt = text("""
        DELETE FROM push_subscriptions
        WHERE endpoint = :endpoint AND user_id = :user_id
    """)
    result = db.execute(stmt, {"user_id": user_id, "endpoint": endpoint})
    db.commit()
    return result.rowcount > 0


def get_user_push_subscriptions(db: Any, user_id: int) -> list[dict[str, Any]]:
    """Get all push subscriptions for a user."""
    from sqlalchemy import text

    stmt = text("""
        SELECT subscription_id, endpoint, p256dh, auth
        FROM push_subscriptions
        WHERE user_id = :user_id
    """)
    result = db.execute(stmt, {"user_id": user_id})
    return [dict(row._mapping) for row in result.fetchall()]


async def subscribe_user(
    user_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Register push subscription for user (upsert by endpoint)."""
    from src.database import SessionLocal

    db = SessionLocal()
    try:
        return upsert_push_subscription(
            db,
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent,
        )
    finally:
        db.close()


async def unsubscribe_user(user_id: int, endpoint: str) -> bool:
    """Remove push subscription for user."""
    from src.database import SessionLocal

    db = SessionLocal()
    try:
        return delete_push_subscription(db, user_id, endpoint)
    finally:
        db.close()


async def send_push_to_user(
    user_id: int,
    title: str,
    body: str,
    url: str = "/",
    data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Send push notification to all user's devices."""
    from src.database import SessionLocal

    db = SessionLocal()
    try:
        subscriptions = get_user_push_subscriptions(db, user_id)
        results = []

        for sub in subscriptions:
            try:
                success = await _send_single_push(sub, title, body, url, data)
                results.append({"subscription_id": sub["subscription_id"], "success": success})
            except SubscriptionExpired:
                # Clean up expired subscription
                delete_push_subscription(db, user_id, sub["endpoint"])
                results.append({"subscription_id": sub["subscription_id"], "success": False, "expired": True})
            except PushError as e:
                logger.warning("Push failed for subscription %s: %s", sub["subscription_id"], e)
                results.append({"subscription_id": sub["subscription_id"], "success": False})

        return results
    finally:
        db.close()


async def _send_single_push(
    subscription: dict[str, Any],
    title: str,
    body: str,
    url: str,
    data: dict[str, Any] | None,
) -> bool:
    """Send push to a single subscription."""
    wp = _init_webpush()
    if wp is None:
        raise PushError("WebPush not configured")

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        **(data or {}),
    })

    try:
        resp = wp.send(
            subscription_info={
                "endpoint": subscription["endpoint"],
                "keys": {
                    "p256dh": subscription["p256dh"],
                    "auth": subscription["auth"],
                },
            },
            data=payload,
        )
        # 404/410 = expired subscription
        if resp.status_code in (404, 410):
            raise SubscriptionExpired()
        # `is_success` chứ KHÔNG phải `resp.ok`: `.ok` là thuộc tính của thư
        # viện `requests`, `httpx.Response` không có nó. Gọi `.ok` ném
        # AttributeError, bị `notifications.py` nuốt, và mọi lượt gửi bị coi
        # như thất bại im lặng.
        return resp.is_success
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (404, 410):
            raise SubscriptionExpired()
        raise PushError(str(e)) from e
