"""Test cấu hình hệ thống.

Điểm đáng canh: DB rỗng phải đọc ra đủ khoá mặc định, và khoá lạ phải bị từ
chối thay vì ghi im lặng vào JSON.
"""

import pytest

from src.services import settings_store


class TestGetSettings:
    def test_empty_db_returns_defaults(self, db_session):
        """Chưa ai đổi gì vẫn đọc ra đủ khoá — không 404, không dict rỗng."""
        result = settings_store.get_settings(db_session)
        assert result == settings_store.DEFAULTS

    def test_stored_value_overrides_default(self, db_session):
        settings_store.update_settings(db_session, {"reports": {"overdueWarningDays": 5}}, user_id=1)
        result = settings_store.get_settings(db_session)
        assert result["reports"]["overdueWarningDays"] == 5

    def test_unchanged_keys_keep_defaults(self, db_session):
        """Đổi một khoá không được làm mất các khoá còn lại.

        DB chỉ lưu phần đã đổi; phần còn lại phải rơi về mặc định trong code.
        """
        settings_store.update_settings(db_session, {"reports": {"overdueWarningDays": 5}}, user_id=1)
        result = settings_store.get_settings(db_session)
        assert (
            result["reports"]["defaultPeriodDays"]
            == settings_store.DEFAULTS["reports"]["defaultPeriodDays"]
        )


class TestUpdateSettings:
    def test_partial_update(self, db_session):
        result = settings_store.update_settings(
            db_session, {"reports": {"defaultPeriodDays": 90}}, user_id=1
        )
        assert result["reports"]["defaultPeriodDays"] == 90

    def test_second_update_overwrites(self, db_session):
        settings_store.update_settings(db_session, {"reports": {"defaultPeriodDays": 90}}, user_id=1)
        result = settings_store.update_settings(
            db_session, {"reports": {"defaultPeriodDays": 14}}, user_id=1
        )
        assert result["reports"]["defaultPeriodDays"] == 14

    def test_unknown_group_rejected(self, db_session):
        with pytest.raises(ValueError, match="không hợp lệ"):
            settings_store.update_settings(db_session, {"khong_co": {"x": 1}}, user_id=1)

    def test_unknown_key_rejected(self, db_session):
        """Khoá lạ phải nổ, KHÔNG được ghi im lặng.

        Ghi im lặng thì BQL sửa một cấu hình gõ sai tên, thấy API trả 200, và
        tin rằng cài đặt đã có hiệu lực — trong khi không có gì đọc khoá đó.
        """
        with pytest.raises(ValueError, match="không hợp lệ"):
            settings_store.update_settings(
                db_session, {"reports": {"khongCoKhoaNay": 1}}, user_id=1
            )

    @pytest.mark.parametrize("value", [0, 11, -1])
    def test_overdue_warning_days_out_of_range(self, db_session, value):
        with pytest.raises(ValueError, match="overdueWarningDays"):
            settings_store.update_settings(
                db_session, {"reports": {"overdueWarningDays": value}}, user_id=1
            )

    @pytest.mark.parametrize("value", [6, 366])
    def test_default_period_days_out_of_range(self, db_session, value):
        with pytest.raises(ValueError, match="defaultPeriodDays"):
            settings_store.update_settings(
                db_session, {"reports": {"defaultPeriodDays": value}}, user_id=1
            )

    def test_bool_rejected_for_int_field(self, db_session):
        """`True` là int hợp lệ trong Python — chặn tay, nếu không `True` lọt
        qua kiểm khoảng và biến thành 1 ngày."""
        with pytest.raises(ValueError, match="overdueWarningDays"):
            settings_store.update_settings(
                db_session, {"reports": {"overdueWarningDays": True}}, user_id=1
            )

    def test_records_updated_by(self, db_session):
        from src.models.db import SystemSetting

        settings_store.update_settings(db_session, {"reports": {"defaultPeriodDays": 60}}, user_id=1)
        row = db_session.get(SystemSetting, "reports")
        assert row.updated_by == 1
