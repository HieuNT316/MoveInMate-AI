"""Test hàm đếm ngày làm việc — nền của mọi số liệu đúng hạn trong report.

Hàm thuần nên không cần DB. Đây là chỗ đáng test kỹ: sai một ngày ở đây thì
`onTimeRate` báo sai cho toàn bộ hồ sơ, mà nhìn con số cuối không phát hiện được.
"""

from datetime import UTC, datetime

import pytest

from src.services.reporting import business_days_between

# 2026-08-24 là thứ Hai. Mọi mốc dưới đây tính từ tuần đó cho dễ đối chiếu:
#   T2 24 · T3 25 · T4 26 · T5 27 · T6 28 · T7 29 · CN 30 · T2 31
MON = datetime(2026, 8, 24, 9, 0, tzinfo=UTC)
TUE = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)
FRI = datetime(2026, 8, 28, 9, 0, tzinfo=UTC)
SAT = datetime(2026, 8, 29, 9, 0, tzinfo=UTC)
SUN = datetime(2026, 8, 30, 9, 0, tzinfo=UTC)
NEXT_MON = datetime(2026, 8, 31, 9, 0, tzinfo=UTC)


class TestBusinessDaysBetween:
    def test_same_day_is_zero(self):
        assert business_days_between(MON, MON) == 0

    def test_consecutive_weekdays(self):
        assert business_days_between(MON, TUE) == 1

    def test_within_one_week(self):
        # T2 → T6 = 4 ngày làm việc
        assert business_days_between(MON, FRI) == 4

    def test_weekend_not_counted(self):
        # T6 → T2 tuần sau: chỉ 1 ngày làm việc, T7 và CN bị loại.
        # Đây là ca chính hàm này sinh ra để xử lý — chênh lịch là 3 ngày.
        assert business_days_between(FRI, NEXT_MON) == 1

    def test_friday_to_saturday_is_zero(self):
        # Thứ Bảy không phải ngày làm việc nên không tính thêm ngày nào.
        assert business_days_between(FRI, SAT) == 0

    def test_saturday_to_sunday_is_zero(self):
        assert business_days_between(SAT, SUN) == 0

    def test_spans_two_weekends(self):
        # T2 24/08 → T2 07/09 = 2 tuần = 10 ngày làm việc.
        two_weeks_later = datetime(2026, 9, 7, 9, 0, tzinfo=UTC)
        assert business_days_between(MON, two_weeks_later) == 10

    def test_time_of_day_ignored(self):
        """Đếm theo NGÀY LỊCH, không theo số giờ trôi qua.

        Hồ sơ nộp 16:59 và duyệt 09:00 hôm sau đã đi qua một ranh giới ngày
        làm việc, dù chỉ cách nhau 16 tiếng. Cam kết của BQL nói bằng ngày.
        """
        late_mon = datetime(2026, 8, 24, 16, 59, tzinfo=UTC)
        early_tue = datetime(2026, 8, 25, 8, 1, tzinfo=UTC)
        assert business_days_between(late_mon, early_tue) == 1

    def test_reversed_order_returns_zero(self):
        """Mốc kết thúc trước mốc bắt đầu → 0, không âm.

        Xảy ra được khi đồng hồ lệch hoặc dữ liệu audit ghi sai thứ tự. Số âm
        sẽ kéo trung bình xuống một cách âm thầm; 0 thì vô hại và không giấu.
        """
        assert business_days_between(TUE, MON) == 0

    def test_naive_datetime_accepted(self):
        """SQLite trả datetime không có tzinfo; hàm không được vỡ vì điều đó."""
        naive_mon = datetime(2026, 8, 24, 9, 0)
        naive_fri = datetime(2026, 8, 28, 9, 0)
        assert business_days_between(naive_mon, naive_fri) == 4

    def test_mixed_naive_and_aware(self):
        """Trộn hai loại: `applications.created_at` và `audit_log.created_at`
        có thể đến từ hai đường khác nhau. So sánh trực tiếp sẽ ném TypeError.
        """
        naive_mon = datetime(2026, 8, 24, 9, 0)
        assert business_days_between(naive_mon, FRI) == 4
        assert business_days_between(MON, datetime(2026, 8, 28, 9, 0)) == 4

    @pytest.mark.parametrize("missing", ["start", "end"])
    def test_none_returns_none(self, missing):
        """Thiếu mốc → None, KHÔNG phải 0.

        0 đọc thành "xử lý xong trong ngày" — báo sai theo hướng có lợi. None
        buộc chỗ gọi phải quyết định loại hồ sơ đó khỏi mẫu.
        """
        start = None if missing == "start" else MON
        end = None if missing == "end" else FRI
        assert business_days_between(start, end) is None
