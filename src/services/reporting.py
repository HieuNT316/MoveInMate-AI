"""Tính toán cho Report API (US báo cáo vận hành).

Hai điều cần biết trước khi sửa file này:

1. **Mốc thời gian chuyển trạng thái hồ sơ nằm ở `audit_log`, không ở
   `applications`.** Bảng `applications` chỉ có `created_at`/`updated_at`;
   `updated_at` bị ghi đè mỗi lần sửa bất cứ trường nào nên không dùng làm mốc
   duyệt được. `store.update_application_status` đã ghi `application.status_changed`
   kèm `new_value.status` — đó là nguồn duy nhất biết hồ sơ vào trạng thái nào
   lúc nào.

2. **Thiếu dữ liệu trả `None`, không trả `0`.** Tỉ lệ đúng hạn `0` đọc thành
   "không hồ sơ nào đúng hạn" — báo sai theo hướng có hại. `None` buộc phía gọi
   phải nói rõ "chưa đủ dữ liệu". Mọi hàm ở đây giữ nguyên tắc này.
"""

from __future__ import annotations

from datetime import UTC, datetime

# Thứ Bảy = 5, Chủ nhật = 6 theo `datetime.weekday()`.
_WEEKEND = (5, 6)


def business_days_between(start: datetime | None, end: datetime | None) -> int | None:
    """Số ngày làm việc giữa hai mốc, KHÔNG tính thứ Bảy và Chủ nhật.

    Trả `None` khi thiếu một trong hai mốc — xem nguyên tắc 2 ở đầu file.

    KHÔNG trừ ngày lễ. `data/kb/bql/bql-co-cau-va-quy-trinh.md` dòng 127 nói
    thời hạn không tính cả ngày lễ, nhưng dự án chưa có nguồn dữ liệu ngày lễ và
    tự soạn một bảng là bịa số liệu (bất biến charter). Hệ quả: số ngày báo ra
    có thể CAO hơn thực tế quanh dịp lễ, tức nghiêng về phía khắt khe với BQL —
    sai theo hướng an toàn hơn là ngược lại. Giao diện report phải nói rõ điều này.

    Đếm theo ranh giới NGÀY LỊCH, không theo số giờ: nộp 16:59 và duyệt 09:00
    hôm sau là đã sang một ngày làm việc, dù chỉ cách 16 tiếng. Cam kết của BQL
    phát biểu bằng ngày nên phép đo cũng phải bằng ngày.
    """
    if start is None or end is None:
        return None

    start_date = _as_utc(start).date()
    end_date = _as_utc(end).date()

    # Mốc kết thúc trước mốc bắt đầu: đồng hồ lệch hoặc audit ghi sai thứ tự.
    # Trả 0 thay vì số âm — số âm kéo trung bình xuống một cách âm thầm.
    if end_date <= start_date:
        return 0

    # Đếm thẳng từng ngày. Khoảng cách ở đây tính bằng ngày tới vài tuần, nên
    # vòng lặp rẻ hơn và dễ đọc hơn công thức chia tuần + phần dư.
    days = 0
    current = start_date
    while current < end_date:
        current = current.fromordinal(current.toordinal() + 1)
        if current.weekday() not in _WEEKEND:
            days += 1
    return days


def _as_utc(value: datetime) -> datetime:
    """Chuẩn hoá về UTC, chấp nhận cả datetime không mang múi giờ.

    SQLite (dùng trong test) trả datetime naive còn Postgres trả aware. So sánh
    trực tiếp hai loại sẽ ném TypeError, và lỗi đó chỉ lộ ra trên môi trường
    thật chứ không lộ khi chạy test.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
