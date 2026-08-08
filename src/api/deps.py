"""Dependency xác thực.

⚠️ TẠM THỜI — bản demo nhận diện người dùng qua header `X-User-Id`.
Bản thật sẽ verify JWT của Supabase (xem docs/architecture_diagram.md mục 3.2).
Chữ ký hàm giữ nguyên khi thay, nên route không phải sửa.
"""

from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.services import store


async def get_current_user(
    x_user_id: int = Header(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Lấy người dùng hiện tại. Không hợp lệ thì 401."""
    user = store.get_user(db, x_user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không xác thực được người dùng",
        )
    return user


async def require_admin(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Chỉ cho phép tài khoản Ban quản lý. Kiểm tra phía server, không tin client."""
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chức năng này chỉ dành cho Ban quản lý",
        )
    return user
