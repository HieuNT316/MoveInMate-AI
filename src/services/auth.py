"""Xác minh JWT do Supabase Auth cấp (US-01).

Project này ký token bằng **ES256** với cặp khoá bất đối xứng, không phải HS256
với `SUPABASE_JWT_SECRET`. Kiểm chứng ngày 11/08: JWKS endpoint trả 1 khoá
`alg=ES256, kty=EC`, và header token thật cũng là ES256.

Hệ quả: verify phải lấy khoá công khai từ JWKS. Dùng `SUPABASE_JWT_SECRET` sẽ
luôn thất bại — biến đó chỉ còn ý nghĩa với các project Supabase đời cũ.

Backend KHÔNG bao giờ nhận `user_id` do client gửi. Nó đọc `sub` trong token đã
verify rồi tự tra sang `users.auth_user_id`. Client tự khai mình là ai thì việc
phân quyền BQL/cư dân mất hết ý nghĩa.
"""

from __future__ import annotations

import uuid
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from src.config import get_settings


class AuthError(Exception):
    """Token thiếu, sai chữ ký, hết hạn, hoặc không đúng đối tượng."""


@lru_cache
def _jwks_client() -> PyJWKClient:
    """Một client dùng lại cho mọi request — nó tự cache khoá công khai.

    Tạo mới mỗi lần sẽ gọi HTTP tới Supabase trên từng request, cộng thêm
    latency và biến Supabase thành điểm chết cho toàn bộ API.
    """
    settings = get_settings()
    if not settings.supabase_url:
        raise AuthError("Chưa cấu hình SUPABASE_URL")
    return PyJWKClient(
        f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
    )


def verify_token(token: str) -> uuid.UUID:
    """Trả về `sub` của token nếu hợp lệ, ngược lại raise `AuthError`."""
    settings = get_settings()
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=f"{settings.supabase_url}/auth/v1",
        )
    except jwt.PyJWTError as exc:
        raise AuthError(f"Token không hợp lệ: {exc}") from exc

    subject = claims.get("sub")
    if not subject:
        raise AuthError("Token thiếu claim 'sub'")
    try:
        return uuid.UUID(subject)
    except ValueError as exc:
        raise AuthError("Claim 'sub' không phải UUID") from exc


def bearer_token(authorization: str | None) -> str | None:
    """Tách token khỏi header `Authorization: Bearer <token>`."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    return token.strip() if scheme.lower() == "bearer" and token.strip() else None
