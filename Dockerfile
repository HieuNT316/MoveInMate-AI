# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: Production ----
FROM python:3.11-slim

WORKDIR /app

# Security: run as non-root user
RUN useradd -m appuser

# Thư viện phải nằm trong home của appuser. Bản trước copy vào /root/.local rồi
# chuyển sang USER appuser — mà /root có quyền 700 nên appuser không đọc được,
# container sẽ chết ngay khi khởi động.
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY --chown=appuser:appuser . .

# Create data directory with correct ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

# Railway cấp cổng động qua $PORT và bỏ qua EXPOSE; dòng này chỉ để chạy local.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT','8000') + '/health')" || exit 1

# Chạy qua entrypoint thay vì `CMD alembic ... && uvicorn ...`:
#   - `${PORT}` vẫn được khai triển (dạng exec của CMD thì không)
#   - `exec` trong script cho uvicorn nhận thẳng SIGTERM, dừng sạch khi Railway
#     restart. Dạng shell của CMD để uvicorn làm tiến trình con của sh và tín
#     hiệu có thể không tới nơi.
# Gọi qua `sh` nên không phụ thuộc bit thực thi của file — Windows không giữ nó.
#
# Đánh đổi đã biết: nhiều instance cùng chạy `upgrade head` khi scale. Alembic
# có khoá riêng nên an toàn, nhưng cần xem lại nếu sau này chạy nhiều bản sao.
CMD ["sh", "/app/docker-entrypoint.sh"]
