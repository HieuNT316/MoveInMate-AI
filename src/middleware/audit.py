"""Audit logging for sensitive actions."""

from __future__ import annotations

import logging
from typing import Any

from src.models.db import AuditLog

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
    # Dùng ORM chứ KHÔNG dùng `text()` với tham số bind.
    #
    # `old_value`/`new_value` là dict Python. Bind thẳng vào SQL thô thì cả
    # psycopg2 lẫn sqlite3 đều không adapt được kiểu dict:
    #
    #   psycopg2.ProgrammingError: can't adapt type 'dict'
    #   sqlite3.ProgrammingError: Error binding parameter 5: type 'dict'
    #                             is not supported
    #
    # Lỗi đó bị `except` bên dưới nuốt, nên bảng `audit_log` RỖNG HOÀN TOÀN mà
    # không ai biết — kéo theo mọi mốc thời gian của Report API (`_first_reached`
    # trong `src/services/reports.py` đọc chính bảng này) trả None vĩnh viễn.
    # Đo trên Postgres thật ngày 31/08: 0 dòng sau khi gọi, `commit()` vẫn OK
    # nên không có tín hiệu nào lộ ra ngoài.
    #
    # `AuditLog.old_value` khai `JSONType` (JSONB trên Postgres, JSON trên
    # SQLite) nên SQLAlchemy tự serialize đúng.
    try:
        db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_value=old_value,
                new_value=new_value,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        db.flush()  # đẩy INSERT xuống DB ngay để lỗi lộ ra ở đây, không phải ở commit của caller
        # KHÔNG commit ở đây — để caller quản lý transaction.
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")
