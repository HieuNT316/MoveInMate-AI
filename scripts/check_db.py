"""Kiểm tra kết nối DATABASE_URL và báo lỗi theo hướng sửa được.

Chạy:  python -m scripts.check_db

Lý do có script này: lỗi kết nối Supabase gần như luôn hiện ra dưới dạng một
dòng `OperationalError` giống hệt nhau, dù nguyên nhân rất khác — sai mật khẩu,
chọn nhầm chuỗi Direct (chỉ IPv6), hay chọn nhầm cổng 6543. Script tách các
trường hợp đó ra trước khi bạn kịp đoán mò.
"""

from __future__ import annotations

import re
import socket
from urllib.parse import urlparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from src.config import get_settings


def _describe_target(url: str) -> tuple[str | None, int | None]:
    parsed = urlparse(url)
    return parsed.hostname, parsed.port


def _warn_on_url(url: str) -> list[str]:
    """Bắt các cấu hình sai phổ biến ngay trước khi thử kết nối."""
    warnings: list[str] = []
    host, port = _describe_target(url)

    if host and host.startswith("db.") and host.endswith(".supabase.co"):
        warnings.append(
            "Đang dùng chuỗi 'Direct connection'. Supabase chỉ phục vụ nó qua IPv6, "
            "mạng IPv4 sẽ treo rồi timeout. Đổi sang tab 'Session pooler'."
        )
    if port == 6543:
        warnings.append(
            "Cổng 6543 là 'Transaction pooler' (pgbouncer). Alembic sẽ lỗi vì "
            "chế độ này không giữ được prepared statement và DDL trong transaction. "
            "Dùng cổng 5432 của host pooler ('Session pooler')."
        )
    if "pooler.supabase.com" in (host or "") and not re.search(r"//postgres\.[a-z0-9]+:", url):
        warnings.append(
            "Host là pooler nhưng username không có dạng 'postgres.<project-ref>'. "
            "Pooler bắt buộc username kèm project ref."
        )
    if "@" in url and re.search(r"://[^:]+:[^@]*[@:/?#][^@]*@", url):
        warnings.append(
            "Mật khẩu có vẻ chứa ký tự đặc biệt chưa URL-encode (@ : / ? #). "
            "Encode nó, ví dụ '@' thành '%40'."
        )
    return warnings


def _tcp_reachable(host: str, port: int, timeout: float = 8.0) -> tuple[bool, str]:
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        return False, f"không phân giải được tên miền ({exc})"

    families = {info[0] for info in infos}
    only_v6 = families == {socket.AF_INET6}

    for family, socktype, proto, _, sockaddr in infos:
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(timeout)
                sock.connect(sockaddr)
                return True, f"mở được cổng qua {'IPv6' if family == socket.AF_INET6 else 'IPv4'}"
        except OSError:
            continue

    hint = " — host này chỉ có bản ghi IPv6, mạng của bạn nhiều khả năng không có IPv6" if only_v6 else ""
    return False, f"không mở được cổng TCP{hint}"


def main() -> None:
    url = get_settings().database_url
    host, port = _describe_target(url)

    # Che mật khẩu trước khi in ra màn hình.
    safe = re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", url)
    print(f"DATABASE_URL : {safe}")

    if url.startswith("sqlite"):
        print("\nĐang dùng SQLite. Chưa trỏ sang Supabase.")
        return

    for warning in _warn_on_url(url):
        print(f"\n[CANH BAO] {warning}")

    if host and port:
        ok, detail = _tcp_reachable(host, port)
        print(f"\nTCP {host}:{port} -> {'OK' if ok else 'THAT BAI'} ({detail})")
        if not ok:
            print("Chưa tới được máy chủ, chưa cần bàn tới mật khẩu. Sửa host/cổng trước.")
            return

    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
    try:
        with engine.connect() as conn:
            version = conn.execute(text("select version()")).scalar_one()
        print(f"Đăng nhập  : OK — {str(version)[:60]}...")
    except OperationalError as exc:
        message = str(exc.orig) if exc.orig else str(exc)
        print(f"Đăng nhập  : THAT BAI — {message.strip().splitlines()[0]}")
        if "password authentication failed" in message:
            print("→ Sai mật khẩu. Đặt lại ở Settings → Database → Reset database password.")
        elif "Tenant or user not found" in message:
            print("→ Username phải là 'postgres.<project-ref>' khi đi qua pooler.")
        return
    finally:
        engine.dispose()

    tables = sorted(inspect(engine).get_table_names())
    print(f"Bảng hiện có: {tables if tables else 'chưa có bảng nào'}")
    if "alembic_version" not in tables:
        print("→ Chạy tiếp: alembic upgrade head")
    elif "users" in tables:
        print("→ Schema đã sẵn sàng. Nạp dữ liệu: python -m scripts.seed_data")


if __name__ == "__main__":
    main()
