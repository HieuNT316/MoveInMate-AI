# Backend Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement backend infrastructure for Phase 2: RBAC, Push Notifications, Tickets, Batch Approval, Cost Tracking, Document Viewer

**Architecture:** Modular middleware approach — RBAC via dependency injection decorators. Push via web-push library. Tickets via new tables. Batch via optimistic locking.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, web-push, Supabase Storage

**Spec:** `docs/superpowers/specs/2026-08-25-phase-2-design.md`

---

## Global Constraints

- Use existing patterns: `src/api/deps.py` for auth, `src/services/store.py` for DB operations
- All new tables need indexes for common queries
- Alembic migrations for all schema changes
- Env vars: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` for push
- Never log full subscription objects (security)
- `APP_ENV=production` blocks `X-User-Id` header

---

## Task 1: DB Migrations — Phase 2 Tables

**Files:**
- Create: `alembic/versions/YYYYMMDDHHMMSS_create_phase2_tables.py`
- Test: Check migration runs successfully

### Steps

- [ ] **Step 1: Create migration for Phase 2 tables**

```python
"""create_phase2_tables

Revision ID: xxxxx
Revises: ddfa7af31680
Create Date: 2026-08-25

"""
from alembic import op
import sqlalchemy as sa

revision = 'xxxxx'
down_revision = 'ddfa7af31680'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # push_subscriptions
    op.create_table(
        'push_subscriptions',
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.String(length=500), nullable=False),
        sa.Column('p256dh', sa.String(length=256), nullable=False),
        sa.Column('auth', sa.String(length=128), nullable=False),
        sa.Column('user_agent', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('subscription_id'),
        sa.UniqueConstraint('endpoint')
    )
    op.create_index('idx_push_subscriptions_user', 'push_subscriptions', ['user_id'])

    # roles
    op.create_table(
        'roles',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('role_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('role_name')
    )

    # permissions
    op.create_table(
        'permissions',
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.Column('permission_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('permission_id'),
        sa.UniqueConstraint('permission_name')
    )

    # role_permissions
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id']),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.permission_id']),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # departments
    op.create_table(
        'departments',
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('lead_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('department_id')
    )

    # staff_assignments
    op.create_table(
        'staff_assignments',
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id']),
        sa.PrimaryKeyConstraint('assignment_id'),
        sa.UniqueConstraint('user_id', 'department_id')
    )

    # tickets
    op.create_table(
        'tickets',
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='open', nullable=True),
        sa.Column('priority', sa.String(length=20), server_default='normal', nullable=True),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.user_id']),
        sa.PrimaryKeyConstraint('ticket_id')
    )
    op.create_index('idx_tickets_user', 'tickets', ['user_id'])
    op.create_index('idx_tickets_status', 'tickets', ['status'])
    op.create_index('idx_tickets_assigned', 'tickets', ['assigned_to'])

    # ticket_messages
    op.create_table(
        'ticket_messages',
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('sender_type', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.ticket_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('message_id')
    )
    op.create_index('idx_messages_ticket', 'ticket_messages', ['ticket_id'])

    # notifications
    op.create_table(
        'notifications',
        sa.Column('notification_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('notification_id')
    )
    op.create_index('idx_notifications_user', 'notifications', ['user_id', 'is_read', 'created_at'])

    # audit_log
    op.create_table(
        'audit_log',
        sa.Column('audit_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('audit_id')
    )

    # user_badges
    op.create_table(
        'user_badges',
        sa.Column('badge_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('badge_key', sa.String(length=50), nullable=False),
        sa.Column('earned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('badge_id'),
        sa.UniqueConstraint('user_id', 'badge_key')
    )

    # usage_logs (cost tracking)
    op.create_table(
        'usage_logs',
        sa.Column('log_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('operation', sa.String(length=50), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('log_id')
    )

    # Add columns to existing users table
    op.add_column('users', sa.Column('role', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('department_id', sa.Integer(), nullable=True))

    # Add version column to applications for optimistic locking
    op.add_column('applications', sa.Column('version', sa.Integer(), server_default='1', nullable=True))
    op.add_column('applications', sa.Column('assigned_to', sa.Integer(), nullable=True))
    op.create_index('idx_applications_assigned', 'applications', ['assigned_to'])


def downgrade() -> None:
    # Reverse all changes
    op.drop_index('idx_applications_assigned', 'applications')
    op.drop_column('applications', 'assigned_to')
    op.drop_column('applications', 'version')
    op.drop_table('usage_logs')
    op.drop_table('user_badges')
    op.drop_table('audit_log')
    op.drop_index('idx_notifications_user', 'notifications')
    op.drop_table('notifications')
    op.drop_index('idx_messages_ticket', 'ticket_messages')
    op.drop_table('ticket_messages')
    op.drop_index('idx_tickets_assigned', 'tickets')
    op.drop_index('idx_tickets_status', 'tickets')
    op.drop_index('idx_tickets_user', 'tickets')
    op.drop_table('tickets')
    op.drop_table('staff_assignments')
    op.drop_table('departments')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_index('idx_push_subscriptions_user', 'push_subscriptions')
    op.drop_table('push_subscriptions')
    op.drop_column('users', 'department_id')
    op.drop_column('users', 'role')
```

- [ ] **Step 2: Run migration**

Run: `alembic upgrade head`
Expected: Migration applies successfully

- [ ] **Step 3: Verify tables exist**

Run: `python -c "from src.database import engine; from sqlalchemy import inspect; print([t for t in inspect(engine).get_table_names()])"`
Expected: New tables appear in list

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/YYYYMMDDHHMMSS_create_phase2_tables.py
git commit -m "db: Phase 2 tables (roles, permissions, departments, tickets, notifications, etc.)"
```

---

## Task 2: RBAC Middleware

**Files:**
- Create: `src/middleware/rbac.py`
- Create: `src/models/rbac.py`
- Modify: `src/api/deps.py` (add permission checks)
- Test: `tests/test_rbac.py`

### Steps

- [ ] **Step 1: Create RBAC models**

```python
# src/models/rbac.py
from enum import Enum


class Permission(str, Enum):
    # Applications
    VIEW_ALL_APPLICATIONS = "view_all_applications"
    VIEW_DEPARTMENT_APPLICATIONS = "view_department_applications"
    VIEW_ASSIGNED_APPLICATIONS = "view_assigned_applications"
    PROCESS_APPLICATION = "process_application"
    APPROVE_APPLICATION = "approve_application"
    BATCH_APPROVE = "batch_approve"

    # Tickets
    VIEW_ALL_TICKETS = "view_all_tickets"
    VIEW_DEPARTMENT_TICKETS = "view_department_tickets"
    ASSIGN_TICKET = "assign_ticket"
    REPLY_TICKET = "reply_ticket"

    # Users
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"

    # Reports
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"

    # Settings
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_DEPARTMENTS = "manage_departments"
    MANAGE_FAQ = "manage_faq"

    # System
    AUDIT_LOG = "audit_log"


ROLE_PERMISSIONS: dict[str, list[Permission]] = {
    "super_admin": list(Permission),
    "admin": [
        Permission.VIEW_ALL_APPLICATIONS,
        Permission.PROCESS_APPLICATION,
        Permission.APPROVE_APPLICATION,
        Permission.BATCH_APPROVE,
        Permission.VIEW_ALL_TICKETS,
        Permission.ASSIGN_TICKET,
        Permission.REPLY_TICKET,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.MANAGE_FAQ,
    ],
    "manager": [
        Permission.VIEW_DEPARTMENT_APPLICATIONS,
        Permission.PROCESS_APPLICATION,
        Permission.APPROVE_APPLICATION,
        Permission.BATCH_APPROVE,
        Permission.VIEW_DEPARTMENT_TICKETS,
        Permission.ASSIGN_TICKET,
        Permission.REPLY_TICKET,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
    ],
    "staff": [
        Permission.VIEW_ASSIGNED_APPLICATIONS,
        Permission.PROCESS_APPLICATION,
        Permission.VIEW_REPORTS,
    ],
    "resident": [],  # No admin permissions
}
```

- [ ] **Step 2: Create RBAC middleware**

```python
# src/middleware/rbac.py
from functools import wraps
from typing import Any, Callable

from fastapi import HTTPException, status

from src.models.rbac import Permission, ROLE_PERMISSIONS


def has_permission(user: dict[str, Any], permission: Permission) -> bool:
    """Check if user has a specific permission."""
    role = user.get("role", "resident")
    permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in permissions


def require_permission(permission: Permission) -> Callable:
    """Decorator to require a specific permission."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs (injected by Depends)
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )

            if not has_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def can_access_application(user: dict[str, Any], application: dict[str, Any]) -> bool:
    """Check if user can access a specific application."""
    role = user.get("role")

    if role == "super_admin":
        return True

    if role in ("admin", "manager"):
        return True

    if role == "staff":
        # Staff can only access assigned applications
        return application.get("assigned_to") == user.get("user_id")

    return False
```

- [ ] **Step 3: Write tests for RBAC**

```python
# tests/test_rbac.py
import pytest
from src.middleware.rbac import has_permission, can_access_application
from src.models.rbac import Permission


def test_super_admin_has_all_permissions():
    user = {"role": "super_admin"}
    for perm in Permission:
        assert has_permission(user, perm)


def test_admin_has_application_permissions():
    user = {"role": "admin"}
    assert has_permission(user, Permission.VIEW_ALL_APPLICATIONS)
    assert has_permission(user, Permission.APPROVE_APPLICATION)
    assert has_permission(user, Permission.MANAGE_FAQ)


def test_staff_has_limited_permissions():
    user = {"role": "staff"}
    assert has_permission(user, Permission.VIEW_ASSIGNED_APPLICATIONS)
    assert not has_permission(user, Permission.VIEW_ALL_APPLICATIONS)
    assert not has_permission(user, Permission.MANAGE_USERS)


def test_resident_has_no_admin_permissions():
    user = {"role": "resident"}
    assert not has_permission(user, Permission.VIEW_ALL_APPLICATIONS)
    assert not has_permission(user, Permission.APPROVE_APPLICATION)


def test_can_access_application_super_admin():
    user = {"role": "super_admin", "user_id": 1}
    app = {"assigned_to": 999}
    assert can_access_application(user, app)


def test_can_access_application_staff_assigned():
    user = {"role": "staff", "user_id": 5}
    app = {"assigned_to": 5}
    assert can_access_application(user, app)


def test_cannot_access_application_staff_not_assigned():
    user = {"role": "staff", "user_id": 5}
    app = {"assigned_to": 999}
    assert not can_access_application(user, app)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_rbac.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add src/middleware/rbac.py src/models/rbac.py tests/test_rbac.py
git commit -m "feat: RBAC middleware and permission system"
```

---

## Task 3: Push Subscriptions API

**Files:**
- Create: `src/services/push.py`
- Modify: `src/api/routes.py` (add push endpoints)
- Modify: `src/config.py` (add VAPID env vars)
- Test: `tests/test_push.py`

### Steps

- [ ] **Step 1: Add VAPID config**

```python
# src/config.py (add to get_settings)
class Settings(BaseSettings):
    # ... existing fields ...

    # VAPID keys for Web Push
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = ""

    @property
    def has_vapid_keys(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)
```

- [ ] **Step 2: Create push service**

```python
# src/services/push.py
import json
import logging
from typing import Any

import httpx
from webpush import WebPush, utils

from src.config import get_settings
from src.database import SessionLocal
from src.services import store

logger = logging.getLogger(__name__)


class PushError(Exception):
    """Push notification failed."""
    pass


class SubscriptionExpired(PushError):
    """Subscription no longer valid."""
    pass


def init_webpush() -> WebPush | None:
    """Initialize web-push with VAPID keys."""
    settings = get_settings()
    if not settings.has_vapid_keys:
        logger.warning("VAPID keys not configured, push disabled")
        return None

    return WebPush(
        public_key=settings.vapid_public_key,
        private_key=settings.vapid_private_key,
        subscriber_email=settings.vapid_subject,
    )


async def subscribe_user(
    user_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str | None = None,
) -> dict[str, Any]:
    """Register push subscription for user (upsert by endpoint)."""
    db = SessionLocal()
    try:
        return store.upsert_push_subscription(
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
    db = SessionLocal()
    try:
        return store.delete_push_subscription(db, user_id, endpoint)
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
    db = SessionLocal()
    try:
        subscriptions = store.get_user_push_subscriptions(db, user_id)
        results = []

        for sub in subscriptions:
            try:
                success = await _send_single_push(sub, title, body, url, data)
                results.append({"subscription_id": sub["subscription_id"], "success": success})
            except SubscriptionExpired:
                # Clean up expired subscription
                store.delete_push_subscription(db, user_id, sub["endpoint"])
                results.append({"subscription_id": sub["subscription_id"], "success": False, "expired": True})
            except PushError as e:
                logger.warning(f"Push failed for subscription {sub['subscription_id']}: {e}")
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
    wp = init_webpush()
    if not wp:
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
        return resp.ok
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (404, 410):
            raise SubscriptionExpired()
        raise PushError(str(e)) from e
```

- [ ] **Step 3: Add push endpoints to routes**

```python
# In src/api/routes.py, add:

@router.post("/push/subscriptions")
async def subscribe_push(
    payload: PushSubscriptionRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Register push notification subscription."""
    result = await push.subscribe_user(
        user_id=user["user_id"],
        endpoint=payload.endpoint,
        p256dh=payload.keys["p256dh"],
        auth=payload.keys["auth"],
        user_agent=payload.user_agent,
    )
    return {"subscription_id": result["subscription_id"]}


@router.delete("/push/subscriptions")
async def unsubscribe_push(
    payload: PushUnsubscribeRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Remove push notification subscription."""
    deleted = await push.unsubscribe_user(user["user_id"], payload.endpoint)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found")


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict[str, str]  # {p256dh, auth}
    user_agent: str | None = None


class PushUnsubscribeRequest(BaseModel):
    endpoint: str
```

- [ ] **Step 4: Add store methods**

```python
# In src/services/store.py, add methods:

def upsert_push_subscription(
    db: Session,
    user_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str | None,
) -> dict[str, Any]:
    """Upsert push subscription."""
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


def delete_push_subscription(db: Session, user_id: int, endpoint: str) -> bool:
    """Delete push subscription (only if owned by user)."""
    stmt = text("""
        DELETE FROM push_subscriptions
        WHERE endpoint = :endpoint AND user_id = :user_id
    """)
    result = db.execute(stmt, {"user_id": user_id, "endpoint": endpoint})
    db.commit()
    return result.rowcount > 0


def get_user_push_subscriptions(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Get all push subscriptions for a user."""
    stmt = text("""
        SELECT subscription_id, endpoint, p256dh, auth
        FROM push_subscriptions
        WHERE user_id = :user_id
    """)
    result = db.execute(stmt, {"user_id": user_id})
    return [dict(row._mapping) for row in result.fetchall()]
```

- [ ] **Step 5: Write tests**

```python
# tests/test_push.py
import pytest
from unittest.mock import AsyncMock, patch

from src.services.push import subscribe_user, unsubscribe_user, send_push_to_user


@pytest.mark.asyncio
async def test_subscribe_user():
    with patch("src.services.push.store") as mock_store:
        mock_store.upsert_push_subscription.return_value = {"subscription_id": 1}
        
        result = await subscribe_user(
            user_id=1,
            endpoint="https://fcm.googleapis.com/test",
            p256dh="p256dh_value",
            auth="auth_value",
        )
        
        assert result["subscription_id"] == 1
        mock_store.upsert_push_subscription.assert_called_once()


@pytest.mark.asyncio
async def test_unsubscribe_user():
    with patch("src.services.push.store") as mock_store:
        mock_store.delete_push_subscription.return_value = True
        
        result = await unsubscribe_user(1, "https://fcm.googleapis.com/test")
        
        assert result is True
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_push.py -v`

- [ ] **Step 7: Commit**

```bash
git add src/services/push.py src/config.py src/api/routes.py src/services/store.py tests/test_push.py
git commit -m "feat: push notification subscription API"
```

---

## Task 4: Push Triggers on Application Status Change

**Files:**
- Modify: `src/api/routes.py` (add notification calls after status change)
- Create: `src/services/notifications.py`

### Steps

- [ ] **Step 1: Create notifications service**

```python
# src/services/notifications.py
import logging
from typing import Any

from src.database import SessionLocal
from src.services import push, store

logger = logging.getLogger(__name__)


async def notify_application_status_change(
    application: dict[str, Any],
    new_status: str,
    resident_name: str,
    checklist_item_name: str,
) -> None:
    """Send push notification when application status changes."""
    user_id = application["user_id"]
    
    status_messages = {
        "received": ("Hồ sơ đã được gửi", f"Hồ sơ đăng ký {checklist_item_name} đang chờ BQL xử lý."),
        "processing": ("Hồ sơ đang được xử lý", "Hồ sơ của bạn đang được BQL xem xét."),
        "needs_info": ("Hồ sơ cần bổ sung giấy tờ", f"Vui lòng bổ sung giấy tờ cho hồ sơ {checklist_item_name}."),
        "approved": ("Hồ sơ đã được duyệt!", f"Chúc mừng! Hồ sơ {checklist_item_name} đã được duyệt."),
        "rejected": ("Hồ sơ bị từ chối", f"Hồ sơ {checklist_item_name} không được duyệt. Lý do: {application.get('bql_note', 'Không có ghi chú')}."),
    }
    
    if new_status not in status_messages:
        return
    
    title, body = status_messages[new_status]
    url = "/documents"
    
    await push.send_push_to_user(user_id, title, body, url)


async def notify_bql_new_application(
    application: dict[str, Any],
    resident_name: str,
    checklist_item_name: str,
) -> None:
    """Notify BQL when new application is submitted."""
    title = "Có hồ sơ mới cần xử lý"
    body = f"Cư dân {resident_name} vừa nộp hồ sơ {checklist_item_name}."
    url = "/admin/applications"
    
    # TODO: Send to BQL users with admin role
    # For now, log it
    logger.info(f"BQL notification: {title} - {body}")
```

- [ ] **Step 2: Modify application status update to send notifications**

```python
# In src/api/routes.py, update_application_status function:
# After successfully updating status, add:
from src.services.notifications import notify_application_status_change

# Get checklist item name
checklist_item = store.get_checklist_item(db, application["checklist_item_id"])
checklist_name = checklist_item["task_name"] if checklist_item else "thủ tục"

await notify_application_status_change(
    application=application,
    new_status=status_update.status.value,
    resident_name=current_user.get("full_name", ""),
    checklist_item_name=checklist_name,
)
```

- [ ] **Step 3: Commit**

```bash
git add src/services/notifications.py src/api/routes.py
git commit -m "feat: send push notifications on application status change"
```

---

## Task 5: Ticket System API

**Files:**
- Create: `src/services/tickets.py`
- Modify: `src/api/routes.py` (add ticket endpoints)
- Modify: `src/services/store.py` (add ticket CRUD)
- Test: `tests/test_tickets.py`

### Steps

- [ ] **Step 1: Create ticket store methods**

```python
# In src/services/store.py, add:

def create_ticket(
    db: Session,
    user_id: int,
    subject: str,
    initial_message: str | None = None,
) -> dict[str, Any]:
    """Create a new ticket."""
    stmt = text("""
        INSERT INTO tickets (user_id, subject, status, priority)
        VALUES (:user_id, :subject, 'open', 'normal')
        RETURNING ticket_id, user_id, subject, status, priority, assigned_to, created_at
    """)
    result = db.execute(stmt, {"user_id": user_id, "subject": subject})
    db.commit()
    ticket = dict(result.one()._mapping)

    if initial_message:
        add_ticket_message(db, ticket["ticket_id"], user_id, "resident", initial_message)

    return ticket


def add_ticket_message(
    db: Session,
    ticket_id: int,
    sender_id: int,
    sender_type: str,
    message: str,
) -> dict[str, Any]:
    """Add message to ticket."""
    stmt = text("""
        INSERT INTO ticket_messages (ticket_id, sender_id, sender_type, message)
        VALUES (:ticket_id, :sender_id, :sender_type, :message)
        RETURNING message_id, ticket_id, sender_id, sender_type, message, created_at
    """)
    result = db.execute(stmt, {
        "ticket_id": ticket_id,
        "sender_id": sender_id,
        "sender_type": sender_type,
        "message": message,
    })
    db.commit()
    return dict(result.one()._mapping)


def get_user_tickets(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Get all tickets for a user."""
    stmt = text("""
        SELECT t.*,
               (SELECT message FROM ticket_messages tm WHERE tm.ticket_id = t.ticket_id ORDER BY created_at DESC LIMIT 1) as last_message
        FROM tickets t
        WHERE t.user_id = :user_id
        ORDER BY t.created_at DESC
    """)
    result = db.execute(stmt, {"user_id": user_id})
    return [dict(row._mapping) for row in result.fetchall()]


def get_ticket_with_messages(db: Session, ticket_id: int, user_id: int) -> dict[str, Any] | None:
    """Get ticket with all messages (for resident, only own tickets)."""
    stmt = text("""
        SELECT t.*, u.full_name as assigned_to_name
        FROM tickets t
        LEFT JOIN users u ON t.assigned_to = u.user_id
        WHERE t.ticket_id = :ticket_id AND t.user_id = :user_id
    """)
    result = db.execute(stmt, {"ticket_id": ticket_id, "user_id": user_id})
    row = result.fetchone()
    if not row:
        return None

    ticket = dict(row._mapping)

    msg_stmt = text("""
        SELECT tm.*, u.full_name as sender_name
        FROM ticket_messages tm
        JOIN users u ON tm.sender_id = u.user_id
        WHERE tm.ticket_id = :ticket_id
        ORDER BY tm.created_at ASC
    """)
    msg_result = db.execute(msg_stmt, {"ticket_id": ticket_id})
    ticket["messages"] = [dict(row._mapping) for row in msg_result.fetchall()]

    return ticket


def assign_ticket(db: Session, ticket_id: int, assigned_to: int) -> dict[str, Any]:
    """Assign ticket to a user."""
    stmt = text("""
        UPDATE tickets
        SET assigned_to = :assigned_to, status = 'in_progress', updated_at = NOW()
        WHERE ticket_id = :ticket_id
        RETURNING *
    """)
    result = db.execute(stmt, {"ticket_id": ticket_id, "assigned_to": assigned_to})
    db.commit()
    return dict(result.one()._mapping)


def resolve_ticket(db: Session, ticket_id: int) -> dict[str, Any]:
    """Mark ticket as resolved."""
    stmt = text("""
        UPDATE tickets
        SET status = 'resolved', resolved_at = NOW(), updated_at = NOW()
        WHERE ticket_id = :ticket_id
        RETURNING *
    """)
    result = db.execute(stmt, {"ticket_id": ticket_id})
    db.commit()
    return dict(result.one()._mapping)


def get_all_tickets(
    db: Session,
    status: str | None = None,
    assigned_to: int | None = None,
) -> list[dict[str, Any]]:
    """Get all tickets (for admin)."""
    query = """
        SELECT t.*, u.full_name as user_name, a.full_name as assigned_to_name
        FROM tickets t
        JOIN users u ON t.user_id = u.user_id
        LEFT JOIN users a ON t.assigned_to = a.user_id
        WHERE 1=1
    """
    params = {}
    if status:
        query += " AND t.status = :status"
        params["status"] = status
    if assigned_to:
        query += " AND t.assigned_to = :assigned_to"
        params["assigned_to"] = assigned_to
    query += " ORDER BY t.created_at DESC"

    result = db.execute(text(query), params)
    return [dict(row._mapping) for row in result.fetchall()]
```

- [ ] **Step 2: Add ticket API endpoints**

```python
# In src/api/routes.py, add:

class TicketCreateRequest(BaseModel):
    subject: str
    message: str | None = None


class TicketMessageRequest(BaseModel):
    message: str


class TicketAssignRequest(BaseModel):
    assigned_to: int


@router.post("/tickets", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreateRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new support ticket."""
    ticket = store.create_ticket(
        db,
        user_id=user["user_id"],
        subject=payload.subject,
        initial_message=payload.message,
    )
    return ticket


@router.get("/tickets", response_model=list[dict])
async def list_my_tickets(
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """List current user's tickets."""
    return store.get_user_tickets(db, user["user_id"])


@router.get("/tickets/{ticket_id}", response_model=dict)
async def get_ticket(
    ticket_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Get ticket details with messages."""
    ticket = store.get_ticket_with_messages(db, ticket_id, user["user_id"])
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/tickets/{ticket_id}/messages", response_model=dict)
async def add_ticket_message(
    ticket_id: int,
    payload: TicketMessageRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Add message to ticket."""
    # Verify ticket exists and user owns it
    ticket = store.get_ticket_with_messages(db, ticket_id, user["user_id"])
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    sender_type = "resident" if user["role"] == "resident" else "staff"
    message = store.add_ticket_message(
        db, ticket_id, user["user_id"], sender_type, payload.message
    )
    return message


# Admin endpoints
@router.get("/admin/tickets", response_model=list[dict])
@require_permission(Permission.VIEW_ALL_TICKETS)
async def list_all_tickets(
    status: str | None = None,
    assigned_to: int | None = None,
    current_user: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """List all tickets (admin only)."""
    return store.get_all_tickets(db, status, assigned_to)


@router.patch("/admin/tickets/{ticket_id}/assign", response_model=dict)
@require_permission(Permission.ASSIGN_TICKET)
async def assign_ticket_to_user(
    ticket_id: int,
    payload: TicketAssignRequest,
    current_user: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Assign ticket to a staff member."""
    ticket = store.assign_ticket(db, ticket_id, payload.assigned_to)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/admin/tickets/{ticket_id}/status", response_model=dict)
@require_permission(Permission.ASSIGN_TICKET)
async def update_ticket_status(
    ticket_id: int,
    status_update: str,  # 'open', 'in_progress', 'resolved', 'closed'
    current_user: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Update ticket status."""
    if status_update == "resolved":
        return store.resolve_ticket(db, ticket_id)
    # ... handle other status updates
```

- [ ] **Step 3: Write tests**

```python
# tests/test_tickets.py
import pytest
from unittest.mock import patch, MagicMock

from src.services.store import create_ticket, add_ticket_message


def test_create_ticket():
    with patch("src.services.store.db") as mock_db:
        mock_result = MagicMock()
        mock_result.one.return_value._mapping = {
            "ticket_id": 1,
            "user_id": 1,
            "subject": "Test ticket",
            "status": "open",
        }
        mock_db.execute.return_value = mock_result

        result = create_ticket(db=mock_db, user_id=1, subject="Test ticket")
        
        assert result["ticket_id"] == 1
        assert result["subject"] == "Test ticket"
```

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/test_tickets.py -v`

```bash
git add src/services/store.py src/api/routes.py tests/test_tickets.py
git commit -m "feat: ticket system API"
```

---

## Task 6: Batch Approval + Auto-Assignment

**Files:**
- Modify: `src/api/routes.py` (add batch endpoints)
- Create: `src/services/assignment.py`
- Test: `tests/test_batch.py`

### Steps

- [ ] **Step 1: Create assignment service**

```python
# src/services/assignment.py
import logging
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import text

from src.database import SessionLocal
from src.services import store

logger = logging.getLogger(__name__)


async def get_least_worked_staff(department_id: int) -> int | None:
    """Get staff with least active applications in department."""
    db = SessionLocal()
    try:
        stmt = text("""
            SELECT u.user_id, COUNT(a.application_id) as active_count
            FROM users u
            JOIN staff_assignments sa ON u.user_id = sa.user_id
            LEFT JOIN applications a ON a.assigned_to = u.user_id
                AND a.status NOT IN ('delivered', 'rejected')
            WHERE sa.department_id = :dept_id
                AND u.role = 'staff'
            GROUP BY u.user_id
            ORDER BY active_count ASC
            LIMIT 1
        """)
        result = db.execute(stmt, {"dept_id": department_id})
        row = result.fetchone()
        return row.user_id if row else None
    finally:
        db.close()


async def auto_assign_on_approval(application_id: int) -> int | None:
    """Auto-assign application to least-worked staff after approval."""
    db = SessionLocal()
    try:
        # Get checklist item to determine department
        stmt = text("""
            SELECT ci.department_id
            FROM applications a
            JOIN checklist_items ci ON a.checklist_item_id = ci.id
            WHERE a.application_id = :app_id
        """)
        result = db.execute(stmt, {"app_id": application_id})
        row = result.fetchone()

        if not row or not row.department_id:
            return None

        staff_id = await get_least_worked_staff(row.department_id)
        if staff_id:
            update_stmt = text("""
                UPDATE applications
                SET assigned_to = :staff_id
                WHERE application_id = :app_id
            """)
            db.execute(update_stmt, {"staff_id": staff_id, "app_id": application_id})
            db.commit()

        return staff_id
    finally:
        db.close()
```

- [ ] **Step 2: Add batch approval endpoint**

```python
# In src/api/routes.py:

class BatchApprovalRequest(BaseModel):
    application_ids: list[int]
    action: Literal["approve", "reject"]
    note: str | None = None


class BatchApprovalResponse(BaseModel):
    processed: int
    failed: list[dict[str, Any]]


@router.post("/admin/applications/batch", response_model=BatchApprovalResponse)
@require_permission(Permission.BATCH_APPROVE)
async def batch_approve_applications(
    payload: BatchApprovalRequest,
    current_user: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Batch approve or reject applications."""
    results = {"processed": 0, "failed": []}

    for app_id in payload.application_ids:
        try:
            # Get application
            app = store.get_application(db, app_id)
            if not app:
                results["failed"].append({"id": app_id, "error": "Not found"})
                continue

            # Check permissions
            if not can_access_application(current_user, app):
                results["failed"].append({"id": app_id, "error": "Permission denied"})
                continue

            # Update status
            new_status = "approved" if payload.action == "approve" else "rejected"
            store.update_application_status(
                db, app_id, new_status, payload.note, current_user["user_id"]
            )
            results["processed"] += 1

        except Exception as e:
            logger.error(f"Batch approval failed for {app_id}: {e}")
            results["failed"].append({"id": app_id, "error": str(e)})

    return results


@router.patch("/admin/applications/{app_id}/status")
@require_permission(Permission.APPROVE_APPLICATION)
async def update_application_status(
    app_id: int,
    payload: ApplicationStatusUpdateRequest,
    version: int | None = None,  # For optimistic locking
    current_user: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Update application status with optimistic locking."""
    app = store.get_application(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Optimistic locking check
    if version is not None and app.get("version", 1) != version:
        raise HTTPException(
            status_code=409,
            detail="Application was modified by another user. Please refresh."
        )

    result = store.update_application_status(
        db, app_id, payload.status.value, payload.bql_note, current_user["user_id"]
    )

    # Send notification
    checklist_item = store.get_checklist_item(db, app["checklist_item_id"])
    await notify_application_status_change(
        result,
        payload.status.value,
        "",  # resident name
        checklist_item["task_name"] if checklist_item else "thủ tục"
    )

    return result
```

- [ ] **Step 3: Add optimistic locking to applications table**

```python
# Store method for update with version check
def update_application_status(
    db: Session,
    application_id: int,
    status: str,
    bql_note: str | None,
    reviewed_by: int,
    expected_version: int | None = None,
) -> dict[str, Any]:
    """Update application status with optimistic locking."""
    if expected_version is not None:
        # With version check
        stmt = text("""
            UPDATE applications
            SET status = :status,
                bql_note = :bql_note,
                reviewed_by = :reviewed_by,
                updated_at = NOW(),
                version = version + 1
            WHERE application_id = :app_id AND version = :version
            RETURNING *
        """)
        result = db.execute(stmt, {
            "status": status,
            "bql_note": bql_note,
            "reviewed_by": reviewed_by,
            "app_id": application_id,
            "version": expected_version,
        })
    else:
        # Without version check
        stmt = text("""
            UPDATE applications
            SET status = :status,
                bql_note = :bql_note,
                reviewed_by = :reviewed_by,
                updated_at = NOW(),
                version = COALESCE(version, 0) + 1
            WHERE application_id = :app_id
            RETURNING *
        """)
        result = db.execute(stmt, {
            "status": status,
            "bql_note": bql_note,
            "reviewed_by": reviewed_by,
            "app_id": application_id,
        })

    db.commit()
    return dict(result.one()._mapping)
```

- [ ] **Step 4: Write tests and commit**

```bash
git add src/services/assignment.py src/api/routes.py src/services/store.py tests/test_batch.py
git commit -m "feat: batch approval with optimistic locking and auto-assignment"
```

---

## Task 7: Document Viewer API

**Files:**
- Modify: `src/api/routes.py` (add document content endpoint)
- Modify: `src/services/storage.py` (add signed URL generation)

### Steps

- [ ] **Step 1: Add signed URL generation to storage service**

```python
# In src/services/storage.py, add:

def generate_signed_url(bucket: str, path: str, expires_in: int = 900) -> str:
    """Generate a signed URL for private storage access.

    Args:
        bucket: Storage bucket name
        path: File path within bucket
        expires_in: URL expiration in seconds (default 15 minutes)

    Returns:
        Signed URL that allows temporary access
    """
    from supabase import create_client
    from src.config import get_settings

    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    # Generate signed URL
    response = supabase.storage.from_(bucket).create_signed_url(path, expires_in)
    return response["signedURL"]
```

- [ ] **Step 2: Add document content endpoint**

```python
# In src/api/routes.py:

@router.get("/documents/{document_id}/content")
async def get_document_content(
    document_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Get document content with signed URL."""
    doc = store.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check permissions for internal documents
    if doc.get("source_type") == "bql_internal":
        if user["role"] not in ("admin", "super_admin", "manager"):
            raise HTTPException(status_code=403, detail="Access denied")

    # Generate signed URL (15 min expiry)
    signed_url = storage.generate_signed_url("documents", doc["file_path"], 900)

    return {
        "document_id": doc["document_id"],
        "title": doc["title"],
        "content_type": doc.get("content_type", "application/pdf"),
        "signed_url": signed_url,
        "expires_at": datetime.now() + timedelta(minutes=15),
    }
```

- [ ] **Step 3: Commit**

```bash
git add src/services/storage.py src/api/routes.py
git commit -m "feat: document viewer with signed URLs"
```

---

## Task 8: Cost Tracking

**Files:**
- Create: `src/services/cost_tracking.py`
- Modify: `src/api/routes.py` (add cost tracking to chat endpoint)
- Modify: `src/services/llm.py` (log usage)
- Test: `tests/test_cost_tracking.py`

### Steps

- [ ] **Step 1: Create cost tracking service**

```python
# src/services/cost_tracking.py
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.services import store

logger = logging.getLogger(__name__)

# Pricing (USD per 1M tokens as of 2024)
OPENAI_GPT4O_MINI_INPUT = 0.15  # $0.15 / 1M input
OPENAI_GPT4O_MINI_OUTPUT = 0.60  # $0.60 / 1M output

GOOGLE_EMBEDDING_INPUT = 0.0001  # $0.0001 / 1M tokens (generous estimate)


def calculate_chat_cost(input_tokens: int, output_tokens: int) -> Decimal:
    """Calculate cost for chat completion."""
    input_cost = (Decimal(input_tokens) / 1_000_000) * Decimal(OPENAI_GPT4O_MINI_INPUT)
    output_cost = (Decimal(output_tokens) / 1_000_000) * Decimal(OPENAI_GPT4O_MINI_OUTPUT)
    return input_cost + output_cost


def calculate_embedding_cost(tokens: int) -> Decimal:
    """Calculate cost for embedding."""
    return (Decimal(tokens) / 1_000_000) * Decimal(GOOGLE_EMBEDDING_INPUT)


def log_usage(
    user_id: int | None,
    provider: str,
    model: str,
    operation: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    """Log API usage for cost tracking."""
    db = SessionLocal()
    try:
        cost = Decimal("0")
        if operation == "chat" and input_tokens is not None and output_tokens is not None:
            cost = calculate_chat_cost(input_tokens, output_tokens)
        elif operation == "embedding" and input_tokens is not None:
            cost = calculate_embedding_cost(input_tokens)

        stmt = text("""
            INSERT INTO usage_logs (user_id, provider, model, operation, input_tokens, output_tokens, cost_usd)
            VALUES (:user_id, :provider, :model, :operation, :input_tokens, :output_tokens, :cost)
        """)
        db.execute(stmt, {
            "user_id": user_id,
            "provider": provider,
            "model": model,
            "operation": operation,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
        })
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log usage: {e}")
    finally:
        db.close()


def get_usage_summary(
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    """Get usage summary for dashboard."""
    db = SessionLocal()
    try:
        query = """
            SELECT
                provider,
                model,
                operation,
                COUNT(*) as request_count,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cost_usd) as total_cost
            FROM usage_logs
            WHERE 1=1
        """
        params = {}
        if user_id:
            query += " AND user_id = :user_id"
            params["user_id"] = user_id
        if date_from:
            query += " AND created_at >= :date_from"
            params["date_from"] = date_from
        if date_to:
            query += " AND created_at <= :date_to"
            params["date_to"] = date_to

        query += " GROUP BY provider, model, operation ORDER BY total_cost DESC"

        result = db.execute(text(query), params)
        rows = [dict(row._mapping) for row in result.fetchall()]

        total_cost = sum(row["total_cost"] or 0 for row in rows)

        return {
            "total_cost": total_cost,
            "breakdown": rows,
        }
    finally:
        db.close()
```

- [ ] **Step 2: Integrate with chat endpoint**

```python
# In src/api/routes.py, chat endpoint:
from src.services.cost_tracking import log_usage

# After getting chat response:
if hasattr(response, "usage"):
    log_usage(
        user_id=user["user_id"],
        provider="openai",
        model="gpt-4o-mini",
        operation="chat",
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )
```

- [ ] **Step 3: Add cost tracking endpoint for admin**

```python
# In src/api/routes.py:

@router.get("/admin/usage/summary")
@require_permission(Permission.VIEW_REPORTS)
async def get_usage_summary(
    user_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: dict[str, Any] = Depends(require_admin),
) -> Any:
    """Get usage summary for cost tracking."""
    from datetime import datetime

    date_from_dt = datetime.fromisoformat(date_from) if date_from else None
    date_to_dt = datetime.fromisoformat(date_to) if date_to else None

    return cost_tracking.get_usage_summary(user_id, date_from_dt, date_to_dt)
```

- [ ] **Step 4: Commit**

```bash
git add src/services/cost_tracking.py src/api/routes.py src/services/llm.py tests/test_cost_tracking.py
git commit -m "feat: cost tracking for LLM and embedding usage"
```

---

## Task 9: Audit Log

**Files:**
- Modify: `src/services/store.py` (add audit log method)
- Create: `src/middleware/audit.py`
- Modify: endpoints to call audit log

### Steps

- [ ] **Step 1: Create audit middleware**

```python
# src/middleware/audit.py
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database import SessionLocal

logger = logging.getLogger(__name__)


def log_action(
    user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Log action to audit trail."""
    db = SessionLocal()
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
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")
    finally:
        db.close()
```

- [ ] **Step 2: Add audit calls to key endpoints**

```python
# In application status update:
from src.middleware.audit import log_action

log_action(
    user_id=current_user["user_id"],
    action="application.status_changed",
    resource_type="application",
    resource_id=app_id,
    old_value={"status": app["status"]},
    new_value={"status": new_status},
)
```

- [ ] **Step 3: Commit**

```bash
git add src/middleware/audit.py src/services/store.py
git commit -m "feat: audit logging for sensitive actions"
```

---

## Task 10: Seed Data for Phase 2

**Files:**
- Create: `scripts/seed_phase2.py`

### Steps

- [ ] **Step 1: Create seed script**

```python
# scripts/seed_phase2.py
"""Seed Phase 2 data: roles, permissions, departments, staff accounts."""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import SessionLocal, engine
from sqlalchemy import text


ROLES = [
    ("super_admin", "Full system access"),
    ("manager", "Department management + approval"),
    ("staff", "Process assigned applications"),
    ("admin", "Legacy BQL access"),
]

PERMISSIONS = [
    ("view_all_applications", "View all applications"),
    ("view_department_applications", "View department applications"),
    ("view_assigned_applications", "View assigned applications"),
    ("process_application", "Process application"),
    ("approve_application", "Approve application"),
    ("batch_approve", "Batch approve applications"),
    ("view_all_tickets", "View all tickets"),
    ("view_department_tickets", "View department tickets"),
    ("assign_ticket", "Assign ticket"),
    ("reply_ticket", "Reply to ticket"),
    ("manage_users", "Manage users"),
    ("view_users", "View users"),
    ("view_reports", "View reports"),
    ("export_reports", "Export reports"),
    ("manage_settings", "Manage settings"),
    ("manage_departments", "Manage departments"),
    ("manage_faq", "Manage FAQ"),
    ("audit_log", "View audit log"),
]

DEPARTMENTS = [
    ("Reception", "Tiếp nhận và phân loại hồ sơ"),
    ("Documents", "Kiểm tra và xử lý giấy tờ"),
    ("Cards", "Cấp phát thẻ cư dân, thẻ xe"),
    ("Utilities", "Tiện ích và dịch vụ"),
]


def seed(db: SessionLocal) -> None:
    """Seed Phase 2 data."""
    print("Seeding roles...")
    for role_name, description in ROLES:
        db.execute(text("""
            INSERT INTO roles (role_name, description)
            VALUES (:name, :desc)
            ON CONFLICT (role_name) DO NOTHING
        """), {"name": role_name, "desc": description})
    db.commit()

    print("Seeding permissions...")
    for perm_name, description in PERMISSIONS:
        db.execute(text("""
            INSERT INTO permissions (permission_name, description)
            VALUES (:name, :desc)
            ON CONFLICT (permission_name) DO NOTHING
        """), {"name": perm_name, "desc": description})
    db.commit()

    print("Seeding role_permissions...")
    # super_admin gets all
    result = db.execute(text("SELECT role_id FROM roles WHERE role_name = 'super_admin'"))
    super_admin_id = result.scalar()
    result = db.execute(text("SELECT permission_id FROM permissions"))
    all_perms = [row[0] for row in result.fetchall()]
    for perm_id in all_perms:
        db.execute(text("""
            INSERT INTO role_permissions (role_id, permission_id)
            VALUES (:role_id, :perm_id)
            ON CONFLICT DO NOTHING
        """), {"role_id": super_admin_id, "perm_id": perm_id})
    db.commit()

    # admin gets specific permissions
    admin_perms = [
        "view_all_applications", "process_application", "approve_application",
        "batch_approve", "view_all_tickets", "assign_ticket", "reply_ticket",
        "view_reports", "export_reports", "manage_faq",
    ]
    for perm_name in admin_perms:
        db.execute(text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.role_id, p.permission_id
            FROM roles r, permissions p
            WHERE r.role_name = 'admin' AND p.permission_name = :perm_name
            ON CONFLICT DO NOTHING
        """), {"perm_name": perm_name})
    db.commit()

    print("Seeding departments...")
    for dept_name, description in DEPARTMENTS:
        db.execute(text("""
            INSERT INTO departments (name, description)
            VALUES (:name, :desc)
            ON CONFLICT DO NOTHING
        """), {"name": dept_name, "desc": description})
    db.commit()

    print("Done!")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
```

- [ ] **Step 2: Run seed script**

```bash
python -m scripts.seed_phase2
```

- [ ] **Step 3: Commit**

```bash
git add scripts/seed_phase2.py
git commit -m "feat: seed script for Phase 2 data (roles, permissions, departments)"
```

---

## Task Dependencies Summary

| Task | Dependencies |
|---|---|
| 1. DB Migrations | — |
| 2. RBAC Middleware | 1 |
| 3. Push Subscriptions | 1 |
| 4. Push Triggers | 3 |
| 5. Ticket System | 1, 2 |
| 6. Batch Approval | 2 |
| 7. Document Viewer | 1 |
| 8. Cost Tracking | 1 |
| 9. Audit Log | 1 |
| 10. Seed Data | 1 |

---

**Plan complete.** Ready for subagent-driven or inline execution.
