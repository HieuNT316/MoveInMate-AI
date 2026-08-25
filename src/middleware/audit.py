"""Audit logging for sensitive actions."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)


def log_action(
    db,
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Log action to audit trail.

    Args:
        db: SQLAlchemy session (passed in to allow transactions).
        user_id: ID of the user performing the action.
        action: Action identifier (e.g., "application.status_changed").
        resource_type: Type of resource (e.g., "application", "ticket").
        resource_id: ID of the affected resource.
        old_value: Previous state of the resource.
        new_value: New state of the resource.
        ip_address: Client IP address.
        user_agent: Client user agent string.
    """
    try:
        stmt = text("""
            INSERT INTO audit_log (user_id, action, resource_type, resource_id, old_value, new_value, ip_address, user_agent)
            VALUES (:user_id, :action, :resource_type, :resource_id, :old_value, :new_value, :ip_address, :user_agent)
        """)
        db.execute(stmt, {
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "old_value": old_value,
            "new_value": new_value,
            "ip_address": ip_address,
            "user_agent": user_agent,
        })
        # Do NOT commit here - let the caller manage the transaction
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")
