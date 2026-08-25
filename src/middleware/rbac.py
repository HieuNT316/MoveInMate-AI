"""RBAC middleware - permission checking functions and decorators."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException, status

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


def require_permission(permission: Permission) -> Callable:
    """Decorator to require a specific permission for a route handler.

    Works with FastAPI Depends by wrapping the handler and checking
    the current_user from kwargs (injected by the auth dependency).

    Usage:
        @router.get("/applications")
        @require_permission(Permission.VIEW_ALL_APPLICATIONS)
        async def list_applications(current_user: dict = Depends(get_current_user)):
            ...

    Args:
        permission: The permission required to access the endpoint.

    Returns:
        Decorator function that wraps the handler.
    """
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
