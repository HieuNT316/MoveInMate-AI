"""US-01 — xác thực qua Supabase Auth.

Phần verify chữ ký ES256 đã kiểm chứng bằng token thật lấy từ Supabase (xem
`src/services/auth.py`). Ở đây `verify_token` được thay bằng bản giả để test
tập trung vào phần còn lại: ánh xạ `sub` sang hồ sơ cư dân, phân quyền, và
chốt chặn header dev ở production.
"""

import uuid

import pytest

from src.api import deps
from src.services.auth import AuthError, bearer_token
from tests.conftest import AUTH_UID_OWNER

BEARER = {"Authorization": "Bearer bat-ky-chuoi-nao"}


@pytest.fixture
def token_of(monkeypatch):
    """Giả lập một token đã verify thành công, trả về `sub` chỉ định."""

    def _use(subject: uuid.UUID):
        monkeypatch.setattr(deps, "verify_token", lambda _token: subject)

    return _use


# --- Tách token khỏi header ---------------------------------------------


@pytest.mark.parametrize(
    "header,expected",
    [
        ("Bearer abc", "abc"),
        ("bearer abc", "abc"),
        ("Bearer   abc  ", "abc"),
        ("Basic abc", None),
        ("abc", None),
        ("Bearer ", None),
        ("", None),
        (None, None),
    ],
)
def test_tach_bearer_token(header, expected):
    assert bearer_token(header) == expected


# --- Nhánh JWT ------------------------------------------------------------


@pytest.mark.asyncio
async def test_jwt_hop_le_tra_dung_ho_so(client, token_of):
    token_of(AUTH_UID_OWNER)
    response = await client.get("/api/v1/profile", headers=BEARER)
    assert response.status_code == 200
    assert response.json()["user_id"] == 2


@pytest.mark.asyncio
async def test_token_hong_thi_401(client, monkeypatch):
    def _reject(_token):
        raise AuthError("chữ ký sai")

    monkeypatch.setattr(deps, "verify_token", _reject)
    response = await client.get("/api/v1/profile", headers=BEARER)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_co_tai_khoan_auth_nhung_chua_co_ho_so_thi_403(client, token_of):
    """Đăng nhập được vào Supabase không có nghĩa là đã được BQL cấp hồ sơ."""
    token_of(uuid.UUID("99999999-9999-4999-8999-999999999999"))
    response = await client.get("/api/v1/profile", headers=BEARER)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_jwt_duoc_uu_tien_hon_header_dev(client, token_of):
    """Có cả hai thì JWT thắng — client không tự chọn được mình là ai."""
    token_of(AUTH_UID_OWNER)
    response = await client.get(
        "/api/v1/profile", headers={**BEARER, "X-User-Id": "3"}
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == 2


# --- Chốt chặn ở production ----------------------------------------------


@pytest.mark.asyncio
async def test_header_dev_bi_tu_choi_o_production(client, monkeypatch):
    """Nếu không chặn, bất kỳ ai đặt `X-User-Id` của tài khoản BQL là thành BQL."""
    settings = deps.get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    response = await client.get("/api/v1/profile", headers={"X-User-Id": "2"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_header_dev_van_chay_ngoai_production(client):
    response = await client.get("/api/v1/profile", headers={"X-User-Id": "2"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tai_khoan_bi_khoa_khong_goi_duoc_api(client, db_session):
    from src.models.db import User

    user = db_session.get(User, 2)
    user.account_status = "locked"
    db_session.commit()

    r = await client.get("/api/v1/profile", headers={"X-User-Id": "2"})
    assert r.status_code == 403
    assert "tạm khoá" in r.json()["detail"]


@pytest.mark.asyncio
async def test_tai_khoan_binh_thuong_van_goi_duoc(client):
    r = await client.get("/api/v1/profile", headers={"X-User-Id": "2"})
    assert r.status_code == 200
