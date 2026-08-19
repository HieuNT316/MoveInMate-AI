"""Bộ đếm rate limit thuần (task 18, guardrail V2/C3, `src/services/rate_limit.py`).

Test cấp API (429 thật trên `/chat` và endpoint tải tệp, phân biệt theo
`X-Forwarded-For`) nằm ở `tests/test_api/test_routes.py`. Ở đây chỉ kiểm phần
logic không cần HTTP: `RateLimiter` (cửa sổ cố định, dọn bucket hết hạn) và
`get_client_ip` (đọc `X-Forwarded-For` trước, `request.client.host` sau).
"""

import pytest

from src.services import rate_limit as rl


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    """Đủ bề mặt để `get_client_ip` chạy: `.headers` và `.client.host`."""

    def __init__(self, headers=None, client_host="1.2.3.4"):
        self.headers = headers or {}
        self.client = _FakeClient(client_host) if client_host is not None else None


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    """Đồng hồ giả — mỗi test tự đẩy `now` tới, không `sleep()` thật."""
    state = {"now": 1_000_000.0}
    monkeypatch.setattr(rl, "clock", lambda: state["now"])
    return state


# --- get_client_ip: đọc đúng IP thật đứng sau proxy Railway ---------------


def test_uu_tien_x_forwarded_for_khi_co():
    req = _FakeRequest(headers={"x-forwarded-for": "9.9.9.9, 10.0.0.1"}, client_host="127.0.0.1")
    assert rl.get_client_ip(req) == "9.9.9.9"


def test_khong_co_x_forwarded_for_thi_dung_client_host():
    req = _FakeRequest(headers={}, client_host="203.0.113.5")
    assert rl.get_client_ip(req) == "203.0.113.5"


def test_client_none_tra_unknown():
    """`request.client` có thể là `None` (vd. một số kiểu test transport) —
    không được crash, rơi về một key cố định."""
    req = _FakeRequest(headers={}, client_host=None)
    assert rl.get_client_ip(req) == "unknown"


# --- RateLimiter: lượt thứ N+1 trong cửa sổ bị chặn -----------------------


def test_duoi_han_muc_thi_qua():
    limiter = rl.RateLimiter(limit=3, window_seconds=60)
    for _ in range(3):
        assert limiter.hit("ip-a") is None


def test_lot_thu_n_cong_1_bi_chan_va_co_thoi_gian_cho():
    limiter = rl.RateLimiter(limit=3, window_seconds=60)
    for _ in range(3):
        assert limiter.hit("ip-a") is None
    wait = limiter.hit("ip-a")
    assert wait is not None
    assert wait > 0


# --- Cửa sổ trôi qua thì được gọi lại (đồng hồ giả, không sleep) ----------


def test_het_cua_so_thi_duoc_goi_lai(clock):
    limiter = rl.RateLimiter(limit=2, window_seconds=60)
    assert limiter.hit("ip-a") is None
    assert limiter.hit("ip-a") is None
    assert limiter.hit("ip-a") is not None  # đã chạm ngưỡng trong cửa sổ này

    clock["now"] += 60  # sang cửa sổ mới
    assert limiter.hit("ip-a") is None


# --- Hai IP khác nhau không dùng chung bucket -----------------------------


def test_hai_ip_khac_nhau_khong_dung_chung_bucket():
    """Đây là test khoá lại đúng lỗi dễ mắc nhất: nếu limiter lỡ khoá theo IP
    của proxy (giống nhau cho mọi người) thay vì IP thật, ip-b sẽ bị ăn ké
    hạn mức đã cạn của ip-a."""
    limiter = rl.RateLimiter(limit=1, window_seconds=60)
    assert limiter.hit("ip-a") is None
    assert limiter.hit("ip-a") is not None  # ip-a đã hết hạn mức

    assert limiter.hit("ip-b") is None  # ip-b chưa từng gọi, không bị vạ lây


# --- Bucket hết hạn bị dọn, không tích luỹ vô hạn -------------------------


def test_bucket_het_han_bi_don_khong_tich_luy(clock):
    limiter = rl.RateLimiter(limit=5, window_seconds=60)
    for i in range(50):
        limiter.hit(f"ip-{i}")
    assert limiter.bucket_count() == 50

    clock["now"] += 61  # mọi bucket cũ đều hết hạn cửa sổ
    limiter.hit("ip-moi")  # một lượt gọi bất kỳ kích hoạt việc dọn (on write)
    assert limiter.bucket_count() == 1
