"""Đẩy biến môi trường từ `.env` lên Railway mà không để lộ giá trị.

Chạy:  python -m scripts.railway_env --dry-run   # xem trước, giá trị đã che
       python -m scripts.railway_env             # đẩy thật

Vì sao không gõ tay `railway variable set KEY=value`: giá trị sẽ nằm nguyên
trong lịch sử shell (PSReadLine lưu ra file), và gõ nhầm một ký tự của
`DATABASE_URL` thì lỗi hiện ra dưới dạng "connection refused" rất khó lần.

Script truyền giá trị qua **stdin** (`railway variable set KEY --stdin`) nên
không có secret nào xuất hiện trên dòng lệnh.

CỐ Ý KHÔNG đẩy `PORT`: Railway tự cấp cổng, đặt tay là health check trượt.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from dotenv import dotenv_values

# Chỉ những biến production thật sự cần. Khai tường minh để không lỡ đẩy
# nhầm thứ chỉ dành cho máy cá nhân (vd. AI_LOG_API_KEY, LANGCHAIN_API_KEY).
REQUIRED = [
    "DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_JWT_SECRET",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
]

# Giá trị cố định cho môi trường production, không lấy từ .env.
OVERRIDES = {
    "APP_ENV": "production",
    "CHAT_PROVIDER": "openai",
}


def _mask(value: str) -> str:
    if len(value) <= 12:
        return "***"
    return f"{value[:6]}…{value[-4:]} ({len(value)} ký tự)"


def _check_database_url(url: str) -> list[str]:
    """Cùng bộ kiểm tra như scripts/check_db.py, chặn trước khi đẩy lên."""
    problems = []
    if url.startswith("sqlite"):
        problems.append("DATABASE_URL đang trỏ SQLite — production phải là Supabase")
    if ".supabase.co:5432" in url and "pooler" not in url:
        problems.append("Đang dùng chuỗi Direct (chỉ IPv6) — đổi sang Session pooler")
    if ":6543/" in url:
        problems.append("Cổng 6543 là Transaction pooler — migration sẽ lỗi, dùng 5432")
    return problems


def _set_variable(key: str, value: str) -> None:
    """Đẩy một biến, giá trị đi qua stdin nên không hiện trên dòng lệnh."""
    result = subprocess.run(
        ["railway", "variable", "set", key, "--stdin", "--skip-deploys"],
        input=value,
        text=True,
        capture_output=True,
        shell=sys.platform == "win32",
    )
    if result.returncode != 0:
        raise SystemExit(f"Lỗi khi đặt {key}: {result.stderr.strip()[:200]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Đẩy biến môi trường lên Railway")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in ra, không đẩy")
    parser.add_argument(
        "--cors",
        default="http://localhost:3000",
        help="CORS_ORIGINS — đổi thành domain Vercel sau khi có",
    )
    args = parser.parse_args()

    env = dotenv_values(".env")
    missing = [key for key in REQUIRED if not env.get(key)]
    if missing:
        raise SystemExit(f"Thiếu trong .env: {', '.join(missing)}")

    problems = _check_database_url(env["DATABASE_URL"])
    if problems:
        for problem in problems:
            print(f"[CHAN] {problem}")
        raise SystemExit("Sửa DATABASE_URL trước đã.")

    payload = {key: env[key] for key in REQUIRED}
    payload.update(OVERRIDES)
    payload["CORS_ORIGINS"] = args.cors

    for key, value in payload.items():
        shown = value if key in OVERRIDES or key == "CORS_ORIGINS" else _mask(value)
        print(f"  {key:22} {shown}")

    if args.dry_run:
        print("\n(dry-run — chưa đẩy gì. Bỏ --dry-run để đẩy thật.)")
        return

    print()
    for key, value in payload.items():
        _set_variable(key, value)
        print(f"  đã đặt {key}")

    print(f"\nOK {len(payload)} biến. KHÔNG đặt PORT — Railway tự cấp.")
    print("Tiếp: railway up")


if __name__ == "__main__":
    main()
