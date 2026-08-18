"""Gọi Admin API của Supabase Auth bằng service key (US-00).

Chỉ backend được gọi những hàm này: service key bỏ qua toàn bộ Row Level
Security, lộ ra frontend là mất sạch phân quyền.

Vì sao sinh mật khẩu tạm thay vì gửi lời mời qua email: luồng đúng là
`invite_user_by_email` để cư dân tự đặt mật khẩu, nhưng nó cần SMTP cấu hình
sẵn và địa chỉ email có thật. Dữ liệu demo dùng tên miền không tồn tại
(`@moveinmate.demo`) nên thư không bao giờ tới. Bản mật khẩu tạm chạy được
ngay và giữ đúng nguyên tắc "BQL cấp tài khoản, cư dân không tự đăng ký".
"""

from __future__ import annotations

import secrets
import string
import uuid

import httpx

from src.config import get_settings


class SupabaseAdminError(Exception):
    """Admin API từ chối hoặc không gọi tới được."""


_PASSWORD_ALPHABET = string.ascii_letters + string.digits


def generate_password(length: int = 14) -> str:
    """Mật khẩu tạm cho tài khoản mới. Chỉ chữ và số để đọc qua điện thoại được."""
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


def _config() -> tuple[str, dict[str, str]]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise SupabaseAdminError("Chưa cấu hình SUPABASE_URL / SUPABASE_SERVICE_KEY")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    return f"{settings.supabase_url}/auth/v1", headers


def create_auth_user(email: str, password: str) -> uuid.UUID:
    """Tạo tài khoản đăng nhập, trả về UUID để gắn vào `users.auth_user_id`."""
    base, headers = _config()
    try:
        response = httpx.post(
            f"{base}/admin/users",
            headers=headers,
            json={"email": email, "password": password, "email_confirm": True},
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise SupabaseAdminError(f"Không gọi được Supabase: {exc}") from exc

    if response.status_code >= 400:
        detail = response.json().get("msg") or response.text
        raise SupabaseAdminError(f"Supabase từ chối tạo tài khoản: {detail}")

    return uuid.UUID(response.json()["id"])


def update_auth_password(auth_user_id: uuid.UUID, password: str) -> None:
    """Đặt lại mật khẩu cho một tài khoản đã có. Dùng khi cư dân quên mật khẩu.

    Không gửi thư đặt lại: tài khoản demo dùng tên miền @moveinmate.demo không
    tồn tại nên thư không bao giờ tới. BQL đọc mật khẩu tạm cho cư dân, đúng
    nguyên tắc "BQL cấp tài khoản, cư dân không tự đăng ký".
    """
    base, headers = _config()
    try:
        response = httpx.put(
            f"{base}/admin/users/{auth_user_id}",
            headers=headers,
            json={"password": password},
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise SupabaseAdminError(f"Không gọi được Supabase: {exc}") from exc

    if response.status_code >= 400:
        detail = response.json().get("msg") or response.text
        raise SupabaseAdminError(f"Supabase từ chối đổi mật khẩu: {detail}")
