"""Cấp tài khoản Supabase Auth cho các hồ sơ cư dân đã có (US-00 + US-01).

Chạy:  python -m scripts.provision_auth
       python -m scripts.provision_auth --limit 6      # chỉ vài tài khoản demo
       python -m scripts.provision_auth --password Abc12345!

Cư dân KHÔNG tự đăng ký — Ban quản lý cấp tài khoản. Script này là bản chạy
hàng loạt của quy tắc đó: với mỗi dòng trong `users` chưa có `auth_user_id`, nó
tạo một user trong Supabase Auth rồi ghi ngược UUID vào hồ sơ.

Chạy lại được: hồ sơ đã gắn `auth_user_id` thì bỏ qua; email đã tồn tại bên
Supabase thì lấy lại UUID đó thay vì tạo trùng.

⚠️ Mật khẩu dùng chung cho toàn bộ tài khoản demo — chỉ hợp lệ với dữ liệu giả.
Với cư dân thật, BQL phải gửi lời mời qua email để mỗi người tự đặt mật khẩu.
"""

from __future__ import annotations

import argparse
import uuid

import httpx
from sqlalchemy import select

from src.config import get_settings
from src.database import SessionLocal
from src.models.db import User
from src.services import store

DEMO_PASSWORD = "MoveInMate!2026"


def _admin_headers() -> dict[str, str]:
    key = get_settings().supabase_service_key
    if not key:
        raise SystemExit("Thiếu SUPABASE_SERVICE_KEY trong .env")
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _auth_base() -> str:
    url = get_settings().supabase_url
    if not url:
        raise SystemExit("Thiếu SUPABASE_URL trong .env")
    return f"{url}/auth/v1"


def _existing_auth_users(client: httpx.Client) -> dict[str, str]:
    """Map email -> auth uid cho các tài khoản đã có bên Supabase."""
    found: dict[str, str] = {}
    page = 1
    while True:
        response = client.get(
            f"{_auth_base()}/admin/users",
            headers=_admin_headers(),
            params={"page": page, "per_page": 200},
            timeout=30,
        )
        response.raise_for_status()
        users = response.json().get("users", [])
        if not users:
            break
        for user in users:
            if user.get("email"):
                found[user["email"].lower()] = user["id"]
        page += 1
    return found


def _create_auth_user(client: httpx.Client, email: str, password: str) -> str:
    response = client.post(
        f"{_auth_base()}/admin/users",
        headers=_admin_headers(),
        json={"email": email, "password": password, "email_confirm": True},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Cấp tài khoản Supabase Auth cho cư dân")
    parser.add_argument("--limit", type=int, default=0, help="Chỉ xử lý N hồ sơ đầu (0 = tất cả)")
    parser.add_argument("--password", default=DEMO_PASSWORD, help="Mật khẩu dùng chung cho demo")
    args = parser.parse_args()

    if get_settings().app_env == "production":
        raise SystemExit("Từ chối cấp mật khẩu dùng chung khi APP_ENV=production.")

    session = SessionLocal()
    try:
        pending = list(
            session.scalars(
                select(User).where(User.auth_user_id.is_(None)).order_by(User.user_id)
            )
        )
        if args.limit:
            pending = pending[: args.limit]

        if not pending:
            print("Mọi hồ sơ đã có tài khoản Supabase Auth.")
            return

        with httpx.Client() as client:
            existing = _existing_auth_users(client)
            created = reused = 0

            for user in pending:
                email = user.email.lower()
                auth_id = existing.get(email)
                if auth_id:
                    reused += 1
                else:
                    auth_id = _create_auth_user(client, email, args.password)
                    created += 1
                store.link_auth_user(session, user.user_id, uuid.UUID(auth_id))
                print(f"  {'gan lai' if email in existing else 'tao moi'}  {email}")

        print(f"\nOK  tao {created}, gan lai {reused} tai khoan")
        print(f"    mat khau dung chung: {args.password}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
