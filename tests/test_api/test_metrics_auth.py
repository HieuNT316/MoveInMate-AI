"""Chốt chặn bearer token trên `GET /api/v1/metrics`.

Endpoint này phơi lưu lượng, tỉ lệ lỗi và chi phí LLM mỗi ngày. Trước 30/08 nó
không có `Depends` nào — ai biết địa chỉ đều đọc được.

`get_settings` có `@lru_cache` nên `monkeypatch.setenv` một mình KHÔNG có tác
dụng: giá trị đã bị nhớ từ lần gọi đầu. Phải xoá cache, và phải xoá lại sau mỗi
test để không rò cấu hình sang test khác.
"""

import pytest

from src.config import get_settings

METRICS_URL = "/api/v1/metrics"
TOKEN = "test-metrics-token-123"


@pytest.fixture
def metrics_token(monkeypatch):
    """Đặt `METRICS_TOKEN` và dọn cache của `get_settings` hai đầu."""

    def _set(value: str):
        monkeypatch.setenv("METRICS_TOKEN", value)
        get_settings.cache_clear()
        return value

    yield _set
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_token_rong_thi_cho_qua(client, metrics_token):
    """Mặc định mở: máy dev `docker compose up` phải chạy được ngay.

    Đánh đổi này được ghi rõ ở `src/config.py`; `src/main.py` cảnh báo khi
    APP_ENV=production mà token rỗng.
    """
    metrics_token("")
    resp = await client.get(METRICS_URL)
    assert resp.status_code == 200
    assert "moveinmate_requests_total" in resp.text


@pytest.mark.asyncio
async def test_token_dung_thi_cho_qua(client, metrics_token):
    metrics_token(TOKEN)
    resp = await client.get(METRICS_URL, headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status_code == 200
    assert "moveinmate_requests_total" in resp.text


@pytest.mark.asyncio
async def test_token_sai_tra_404(client, metrics_token):
    """404 chứ không 401 — 401 xác nhận endpoint có thật."""
    metrics_token(TOKEN)
    resp = await client.get(METRICS_URL, headers={"Authorization": "Bearer sai-token"})
    assert resp.status_code == 404
    assert "moveinmate_requests_total" not in resp.text


@pytest.mark.asyncio
async def test_thieu_header_tra_404(client, metrics_token):
    metrics_token(TOKEN)
    resp = await client.get(METRICS_URL)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sai_dinh_dang_header_tra_404(client, metrics_token):
    """Đúng token nhưng thiếu tiền tố `Bearer ` vẫn bị chặn.

    Không nới cho trường hợp này: chấp nhận token trần nghĩa là có hai định
    dạng hợp lệ, và định dạng thứ hai không ai viết vào tài liệu.
    """
    metrics_token(TOKEN)
    resp = await client.get(METRICS_URL, headers={"Authorization": TOKEN})
    assert resp.status_code == 404
