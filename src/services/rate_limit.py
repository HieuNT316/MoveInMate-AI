"""Giới hạn tốc độ theo IP (guardrail V2/C3, `docs/ROLES_AND_PLAN.md`).

Tự viết tay, KHÔNG thêm dependency (`slowapi`, `limits`, ...). `docs/DEPLOY.md`
mục 213 ghi rõ dịch vụ chạy MỘT instance duy nhất (Chroma sống ngay trong tiến
trình FastAPI nên không scale ngang được) — một bộ đếm trong bộ nhớ tiến trình
là đúng đắn ở đây, không cần Redis hay kho chia sẻ.

Đây CHỈ là trần burst theo từng IP (per-phút / per-giờ). KHÔNG có trần tổng số
request/ngày trên toàn hệ thống: một trần như vậy mới thật sự bảo vệ được hạn
mức Google 1000 request/ngày dùng chung cả nhóm, nhưng nếu nó chạm ngưỡng giữa
buổi demo thì trợ lý im lặng HOÀN TOÀN với mọi người — biến một rủi ro bên
ngoài thành một sự cố tự gây ra, đúng thảm hoạ đang cố tránh. Hạn mức ngày vẫn
là rủi ro ĐƯỢC THEO DÕI (xem README), không phải rủi ro được chặn bằng code.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from src.config import get_settings

# Đồng hồ tách ra một biến module-level thay vì gọi `time.time()` trực tiếp
# trong `RateLimiter`: test monkeypatch `rate_limit.clock` để mô phỏng thời
# gian trôi qua cửa sổ mà không cần `sleep()` thật (chậm và không tất định).
clock = time.time


@dataclass
class _Bucket:
    window_start: float
    count: int


class RateLimiter:
    """Bộ đếm cửa sổ cố định (fixed window), khoá theo một `key` bất kỳ
    (ở đây luôn là IP client — xem `get_client_ip`).

    Dọn bucket hết hạn NGAY TRONG `hit()` — dọn khi ghi (không có thread/job
    quét riêng), và mỗi lần dọn quét TOÀN BỘ dict (sweep) thay vì chỉ xoá đúng
    key đang ghi: đơn giản hơn, và tần suất quét tỉ lệ thuận với traffic thật
    nên dict không phình vô hạn theo số IP đã từng gọi — kể cả những IP không
    bao giờ quay lại vẫn bị dọn ở lượt `hit()` kế tiếp của BẤT KỲ key nào.
    """

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[str, _Bucket] = {}

    def hit(self, key: str) -> float | None:
        """Ghi nhận một lượt gọi của `key`.

        Trả `None` nếu còn trong hạn mức (lượt này ĐÃ được tính vào bộ đếm).
        Trả về số giây còn phải chờ nếu vượt hạn mức — lượt vượt ngưỡng KHÔNG
        được cộng thêm vào count, để không đẩy `Retry-After` lùi vô hạn nếu
        client cứ tiếp tục bắn request trong lúc bị chặn.
        """
        now = clock()
        self._evict_expired(now)

        bucket = self._buckets.get(key)
        if bucket is None or now - bucket.window_start >= self.window_seconds:
            self._buckets[key] = _Bucket(window_start=now, count=1)
            return None

        if bucket.count < self.limit:
            bucket.count += 1
            return None

        return self.window_seconds - (now - bucket.window_start)

    def _evict_expired(self, now: float) -> None:
        expired = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.window_start >= self.window_seconds
        ]
        for key in expired:
            del self._buckets[key]

    def clear(self) -> None:
        """Chỉ dùng cho test — xoá sạch trạng thái để mỗi test bắt đầu từ
        cửa sổ trống, tránh test này ăn hết hạn mức của test khác."""
        self._buckets.clear()

    def bucket_count(self) -> int:
        """Chỉ dùng cho test — số bucket đang giữ trong bộ nhớ, để kiểm tra
        bucket hết hạn có thực sự bị dọn hay không."""
        return len(self._buckets)


def get_client_ip(request: Request) -> str:
    """IP của client thật, KHÔNG phải của proxy đứng trước (Railway).

    Railway chấm dứt TLS rồi forward, nên `request.client.host` luôn là địa
    chỉ của proxy cho MỌI request — khoá bộ đếm theo nó sẽ dồn toàn bộ người
    dùng thật vào chung một bucket, một người spam là khoá luôn cả buổi demo.
    Đọc mục ĐẦU TIÊN của `X-Forwarded-For` khi có, rồi mới rơi về
    `request.client.host`.

    Client có thể tự khai giả header này — CHẤP NHẬN đánh đổi đó: nhánh còn
    lại (khoá chung theo IP proxy) gây hại nặng hơn nhiều so với việc một kẻ
    cố ý né giới hạn bằng cách giả header.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _too_many_requests(retry_after: float) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Bạn đang thao tác quá nhanh, vui lòng đợi một chút rồi thử lại.",
        headers={"Retry-After": str(max(1, int(retry_after) + 1))},
    )


def rate_limit_dependency(*limiters: RateLimiter):
    """Tạo FastAPI dependency áp một hoặc nhiều `RateLimiter` lên cùng một IP.

    Dùng cho `/chat` (10/phút VÀ 100/giờ — cả hai đều được `hit()`, vượt BẤT
    KỲ ngưỡng nào cũng trả 429; `Retry-After` lấy giá trị chờ lớn nhất trong
    số các ngưỡng đã vượt).
    """

    async def _dependency(request: Request) -> None:
        key = get_client_ip(request)
        retry_after: float | None = None
        for limiter in limiters:
            wait = limiter.hit(key)
            if wait is not None:
                retry_after = wait if retry_after is None else max(retry_after, wait)
        if retry_after is not None:
            raise _too_many_requests(retry_after)

    return _dependency


_settings = get_settings()

chat_minute_limiter = RateLimiter(_settings.chat_rate_limit_per_minute, 60)
chat_hour_limiter = RateLimiter(_settings.chat_rate_limit_per_hour, 3600)
# Hai limiter RIÊNG dù cùng ngưỡng 20/phút: tải tệp (cư dân) và nạp tài liệu
# (BQL) là hai thao tác của hai vai khác nhau — dùng chung một bộ đếm sẽ khiến
# một cư dân tải ảnh dồn dập vô tình ăn vào hạn mức nạp tài liệu của BQL nếu
# tình cờ đứng sau cùng NAT/proxy.
attachment_upload_minute_limiter = RateLimiter(_settings.upload_rate_limit_per_minute, 60)
document_ingest_minute_limiter = RateLimiter(_settings.upload_rate_limit_per_minute, 60)

# Áp cho POST /chat.
enforce_chat_rate_limit = rate_limit_dependency(chat_minute_limiter, chat_hour_limiter)
# Áp cho POST /applications/{id}/attachments.
enforce_attachment_upload_rate_limit = rate_limit_dependency(attachment_upload_minute_limiter)
# Áp cho POST /admin/documents.
enforce_document_ingest_rate_limit = rate_limit_dependency(document_ingest_minute_limiter)


def reset_all() -> None:
    """Chỉ dùng cho test (xem `tests/conftest.py`) — xoá sạch mọi bộ đếm."""
    chat_minute_limiter.clear()
    chat_hour_limiter.clear()
    attachment_upload_minute_limiter.clear()
    document_ingest_minute_limiter.clear()
