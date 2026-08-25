"""RBAC middleware - permission checking utilities."""

from typing import Any

from src.models.rbac import ROLE_PERMISSIONS, Permission


def has_permission(user: dict[str, Any], permission: Permission) -> bool:
    """Check if user has a specific permission.

    Args:
        user: User dict with 'role' key.
        permission: Permission to check.

    Returns:
        True if user has the permission, False otherwise.
    """
    role = user.get("role", "resident")
    permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in permissions


def can_access_application(user: dict[str, Any], application: dict[str, Any]) -> bool:
    """Check if user can access a specific application.

    Rules:
    - super_admin: can access all applications
    - admin/manager: can access all applications
    - staff: can only access applications assigned to them
    - resident: cannot access applications

    Args:
        user: User dict with 'role' and 'user_id' keys.
        application: Application dict with 'assigned_to' key.

    Returns:
        True if user can access the application, False otherwise.
    """
    role = user.get("role")

    if role == "super_admin":
        return True

    if role in ("admin", "manager"):
        return True

    if role == "staff":
        # Staff can only access assigned applications
        return application.get("assigned_to") == user.get("user_id")

    return False
