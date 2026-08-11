#!/bin/sh
set -e

# `exec` để uvicorn THAY THẾ shell chứ không chạy làm tiến trình con. Nếu là
# tiến trình con thì SIGTERM lúc Railway restart chỉ tới được shell, uvicorn
# không kịp đóng kết nối và bị SIGKILL sau thời gian chờ.
#
# Migration chạy trước: Railway free tier không có release phase riêng, không
# làm ở đây thì container lên với DB rỗng.

alembic upgrade head

exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
