"""Dependency xác thực (US-01).

Đường chính là JWT của Supabase: `Authorization: Bearer <access_token>`. Backend
verify chữ ký rồi tra `sub` sang `users.auth_user_id` — không nhận `user_id` do
client tự khai.

Header `X-User-Id` vẫn được chấp nhận nhưng CHỈ ngoài production, để bản demo
đổi persona nhanh và để frontend chuyển dần sang JWT mà không đứt. Ở production
nó bị từ chối thẳng: nếu không, bất kỳ ai cũng đặt `X-User-Id: 1` để thành BQL.
"""

from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_db
from src.services import store
from src.services.auth import AuthError, bearer_token, verify_token

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Không xác thực được người dùng",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_id: int | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Người dùng hiện tại, ưu tiên JWT rồi mới tới lối dev."""
    token = bearer_token(authorization)
    if token:
        try:
            auth_user_id = verify_token(token)
        except AuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        user = store.get_user_by_auth_id(db, auth_user_id)
        if user is None:
            # Tài khoản có trong Supabase Auth nhưng chưa được BQL gắn hồ sơ cư dân.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản chưa được Ban quản lý cấp hồ sơ cư dân",
            )
        return user

    if x_user_id is not None:
        if get_settings().app_env == "production":
            raise _UNAUTHORIZED
        user = store.get_user(db, x_user_id)
        if user is None:
            raise _UNAUTHORIZED
        return user

    raise _UNAUTHORIZED


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
