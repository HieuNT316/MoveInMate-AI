"""Bắt lỗi tập trung (V9, `src/main.py`).

`httpx.ASGITransport` mặc định re-raise exception chưa bắt của app thay vì
trả response — tiện cho debug test nhưng cản việc kiểm 500 thật. Dùng
`raise_app_exceptions=False` (thay vì `client` fixture chuẩn của
`tests/conftest.py`) để lấy đúng response mà một trình duyệt thật sẽ nhận.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api import routes as api_routes
from src.database import get_db
from src.main import UNHANDLED_ERROR_MESSAGE, app

OWNER = {"X-User-Id": "2"}


@pytest_asyncio.fixture
async def client_khong_re_raise(db_session):
    """Như fixture `client` ở conftest, nhưng để app tự trả response 500
    thay vì transport ném lại exception cho code test."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_exception_chua_bat_tra_500_voi_thong_diep_co_dinh_va_request_id(
    client_khong_re_raise, monkeypatch
):
    secret_password = "S3cretSupabasePass!"
    connection_string = (
        f"postgresql://appuser:{secret_password}@db.example.supabase.co:5432/postgres"
    )

    def _raise(*_args, **_kwargs):
        raise RuntimeError(f"could not connect to server: {connection_string}")

    monkeypatch.setattr(api_routes, "_build_checklist", _raise)

    response = await client_khong_re_raise.get("/api/v1/checklist", headers=OWNER)

    assert response.status_code == 500
    body = response.json()
    assert body["message"] == UNHANDLED_ERROR_MESSAGE
    assert "request_id" in body and body["request_id"]
    assert response.headers["X-Request-Id"] == body["request_id"]

    # Nội dung exception (và đặc biệt là mật khẩu) không được lộ ra response.
    raw_body = response.text
    assert secret_password not in raw_body
    assert connection_string not in raw_body
    assert "RuntimeError" not in raw_body


@pytest.mark.asyncio
async def test_httpexception_cua_route_khong_bi_anh_huong(client):
    """404 hiện có (`checklist` không tồn tại) phải giữ nguyên hành vi —
    không bị handler 500 nuốt hay đổi hình dạng response."""
    response = await client.patch(
        "/api/v1/checklist/9999", json={"completed": True}, headers=OWNER
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Không tìm thấy mục này"}
