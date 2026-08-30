"""Test truy vấn báo cáo.

Ba thứ đáng canh nhất, theo đúng thứ tự rủi ro:

1. Hồ sơ quay lại `processing` sau `needs_info` — mốc phải là lần ĐẦU đạt
   trạng thái đóng, không phải lần cuối.
2. Mẫu rỗng trả `None`, không phải `0`.
3. Hồ sơ không có `sla_business_days` bị loại khỏi mẫu đúng hạn, không bị coi
   là trễ.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.models.db import Application, AuditLog, ChecklistItem
from src.services import reports


def _item_with_sla(db, sla: int = 3) -> ChecklistItem:
    return db.query(ChecklistItem).filter(ChecklistItem.sla_business_days == sla).first()


def _make_application(db, *, user_id=2, item=None, status="received", created_at=None):
    app = Application(
        user_id=user_id,
        checklist_item_id=item.checklist_item_id,
        status=status,
        kind="bql_processing",
        created_at=created_at or datetime(2026, 8, 24, 9, 0, tzinfo=UTC),
    )
    db.add(app)
    db.flush()
    return app


def _log_status(db, app, status, at):
    """Ghi một dòng audit như `store.update_application_status` vẫn ghi."""
    db.add(
        AuditLog(
            user_id=1,
            action="application.status_changed",
            resource_type="application",
            resource_id=app.application_id,
            new_value={"status": status},
            created_at=at,
        )
    )
    db.flush()


PERIOD = (datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 9, 30, tzinfo=UTC))


class TestApplicationsReport:
    def test_empty_period_returns_none_not_zero(self, db_session):
        """Chưa có hồ sơ nào đóng → None.

        `0` đọc thành "đúng hạn 0%" — báo sai theo hướng có hại cho BQL.
        """
        result = reports.applications_report(db_session, *PERIOD)
        assert result["summary"]["avgProcessingDays"] is None
        assert result["summary"]["onTimeRate"] is None

    def test_counts_by_status(self, db_session):
        item = _item_with_sla(db_session)
        _make_application(db_session, item=item, status="received")
        _make_application(db_session, item=item, user_id=3, status="processing")
        db_session.commit()

        result = reports.applications_report(db_session, *PERIOD)
        assert result["summary"]["byStatus"]["received"] == 1
        assert result["summary"]["byStatus"]["processing"] == 1
        assert result["summary"]["total"] == 2

    def test_on_time_application(self, db_session):
        """Nộp T2, duyệt T4 = 2 ngày làm việc, SLA 3 → đúng hạn."""
        item = _item_with_sla(db_session, sla=3)
        app = _make_application(
            db_session, item=item, status="approved",
            created_at=datetime(2026, 8, 24, 9, 0, tzinfo=UTC),
        )
        _log_status(db_session, app, "approved", datetime(2026, 8, 26, 9, 0, tzinfo=UTC))
        db_session.commit()

        result = reports.applications_report(db_session, *PERIOD)
        assert result["summary"]["avgProcessingDays"] == 2
        assert result["summary"]["onTimeRate"] == 1.0

    def test_late_application(self, db_session):
        """Nộp T2, duyệt T2 tuần sau = 5 ngày làm việc, SLA 3 → trễ."""
        item = _item_with_sla(db_session, sla=3)
        app = _make_application(
            db_session, item=item, status="approved",
            created_at=datetime(2026, 8, 24, 9, 0, tzinfo=UTC),
        )
        _log_status(db_session, app, "approved", datetime(2026, 8, 31, 9, 0, tzinfo=UTC))
        db_session.commit()

        result = reports.applications_report(db_session, *PERIOD)
        assert result["summary"]["onTimeRate"] == 0.0

    def test_uses_first_time_reaching_closed_status(self, db_session):
        """Hồ sơ đi approved → needs_info → approved: lấy mốc ĐẦU.

        Lấy mốc cuối sẽ tính cả quãng chờ cư dân bổ sung giấy tờ vào thời gian
        xử lý của BQL — đổ lỗi sai chỗ.
        """
        item = _item_with_sla(db_session, sla=3)
        app = _make_application(
            db_session, item=item, status="approved",
            created_at=datetime(2026, 8, 24, 9, 0, tzinfo=UTC),
        )
        _log_status(db_session, app, "approved", datetime(2026, 8, 26, 9, 0, tzinfo=UTC))
        _log_status(db_session, app, "needs_info", datetime(2026, 8, 27, 9, 0, tzinfo=UTC))
        _log_status(db_session, app, "approved", datetime(2026, 9, 10, 9, 0, tzinfo=UTC))
        db_session.commit()

        result = reports.applications_report(db_session, *PERIOD)
        assert result["summary"]["avgProcessingDays"] == 2

    def test_no_sla_excluded_from_on_time_rate(self, db_session):
        """Thủ tục không có SLA không được tính là trễ.

        "Theo lịch nhà mạng" không phải cam kết của BQL; đếm nó vào tỉ lệ đúng
        hạn là chấm điểm BQL bằng việc của bên thứ ba.
        """
        item = (
            db_session.query(ChecklistItem)
            .filter(ChecklistItem.sla_business_days.is_(None))
            .filter(ChecklistItem.item_type == "bql_actionable")
            .first()
        )
        app = _make_application(
            db_session, item=item, status="approved",
            created_at=datetime(2026, 8, 24, 9, 0, tzinfo=UTC),
        )
        _log_status(db_session, app, "approved", datetime(2026, 9, 20, 9, 0, tzinfo=UTC))
        db_session.commit()

        result = reports.applications_report(db_session, *PERIOD)
        assert result["summary"]["onTimeRate"] is None
        assert result["coverage"]["excludedNoSla"] == 1

    def test_missing_audit_excluded_and_reported(self, db_session):
        """Hồ sơ đóng nhưng không có dòng audit → loại khỏi mẫu, báo qua coverage."""
        item = _item_with_sla(db_session, sla=3)
        _make_application(db_session, item=item, status="approved")
        db_session.commit()

        result = reports.applications_report(db_session, *PERIOD)
        assert result["coverage"]["excludedNoAudit"] == 1
        assert result["summary"]["avgProcessingDays"] is None

    def test_rejected_counted_in_processing_time(self, db_session):
        """Hồ sơ bị từ chối vẫn tốn công xử lý — tính vào trung bình."""
        item = _item_with_sla(db_session, sla=3)
        app = _make_application(
            db_session, item=item, status="rejected",
            created_at=datetime(2026, 8, 24, 9, 0, tzinfo=UTC),
        )
        _log_status(db_session, app, "rejected", datetime(2026, 8, 26, 9, 0, tzinfo=UTC))
        db_session.commit()

        result = reports.applications_report(db_session, *PERIOD)
        assert result["summary"]["avgProcessingDays"] == 2

    def test_period_filter_excludes_outside(self, db_session):
        item = _item_with_sla(db_session)
        _make_application(
            db_session, item=item, created_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
        )
        db_session.commit()

        result = reports.applications_report(db_session, *PERIOD)
        assert result["summary"]["total"] == 0

    def test_overdue_lists_open_past_sla(self, db_session):
        item = _item_with_sla(db_session, sla=3)
        _make_application(
            db_session, item=item, status="processing",
            created_at=datetime.now(UTC) - timedelta(days=30),
        )
        db_session.commit()

        result = reports.applications_report(db_session, *PERIOD)
        assert result["overdueTotal"] == 1
        assert result["overdue"][0]["slaBusinessDays"] == 3
        assert result["overdue"][0]["businessDaysElapsed"] > 3

    def test_closed_application_never_overdue(self, db_session):
        """Hồ sơ đã đóng không nằm trong danh sách quá hạn dù xử lý lâu."""
        item = _item_with_sla(db_session, sla=3)
        app = _make_application(
            db_session, item=item, status="delivered",
            created_at=datetime.now(UTC) - timedelta(days=60),
        )
        _log_status(db_session, app, "delivered", datetime.now(UTC))
        db_session.commit()

        assert reports.applications_report(db_session, *PERIOD)["overdueTotal"] == 0

    def test_overdue_limit_caps_list_not_total(self, db_session):
        item = _item_with_sla(db_session, sla=3)
        old = datetime.now(UTC) - timedelta(days=30)
        for uid in (2, 3, 4):
            _make_application(db_session, user_id=uid, item=item, status="processing",
                              created_at=old)
        db_session.commit()

        result = reports.applications_report(db_session, *PERIOD, overdue_limit=2)
        assert len(result["overdue"]) == 2
        assert result["overdueTotal"] == 3

    def test_trends_have_one_row_per_day_with_data(self, db_session):
        item = _item_with_sla(db_session)
        _make_application(
            db_session, item=item, created_at=datetime(2026, 8, 24, 9, 0, tzinfo=UTC)
        )
        _make_application(
            db_session, user_id=3, item=item,
            created_at=datetime(2026, 8, 24, 15, 0, tzinfo=UTC),
        )
        db_session.commit()

        trends = reports.applications_report(db_session, *PERIOD)["trends"]
        day = next(t for t in trends if t["date"] == "2026-08-24")
        assert day["created"] == 2


class TestDepartmentsReport:
    def test_groups_by_handling_department(self, db_session):
        item = _item_with_sla(db_session)
        _make_application(db_session, item=item, status="processing")
        db_session.commit()

        result = reports.departments_report(db_session, *PERIOD)
        dept = next(
            d for d in result["departments"]
            if d["handlingDepartment"] == item.handling_department
        )
        assert dept["total"] == 1
        assert dept["open"] == 1

    def test_unassigned_counted(self, db_session):
        item = _item_with_sla(db_session)
        _make_application(db_session, item=item, status="processing")
        db_session.commit()

        result = reports.departments_report(db_session, *PERIOD)
        dept = next(
            d for d in result["departments"]
            if d["handlingDepartment"] == item.handling_department
        )
        assert dept["unassigned"] == 1

    def test_filter_by_department(self, db_session):
        item = _item_with_sla(db_session)
        _make_application(db_session, item=item, status="processing")
        db_session.commit()

        result = reports.departments_report(
            db_session, *PERIOD, department=item.handling_department
        )
        assert len(result["departments"]) == 1


class TestStaffReport:
    def test_metrics_by_assigned_to(self, db_session):
        item = _item_with_sla(db_session)
        app = _make_application(db_session, item=item, status="processing")
        app.assigned_to = 1
        db_session.commit()

        result = reports.staff_report(db_session, *PERIOD)
        assert result["basis"] == "assigned_to"
        staff = next(s for s in result["staff"] if s["staffId"] == 1)
        assert staff["assigned"] == 1
        assert staff["open"] == 1

    def test_unassigned_kept_separate(self, db_session):
        """Hồ sơ chưa gán ai KHÔNG được gộp vào một 'nhân viên ảo'.

        Gộp sẽ làm sai mọi trung bình của người thật.
        """
        item = _item_with_sla(db_session)
        _make_application(db_session, item=item, status="processing")
        db_session.commit()

        result = reports.staff_report(db_session, *PERIOD)
        assert result["unassigned"]["open"] == 1
        assert all(s["assigned"] == 0 for s in result["staff"])

    def test_outcome_rates_none_when_nothing_closed(self, db_session):
        item = _item_with_sla(db_session)
        app = _make_application(db_session, item=item, status="processing")
        app.assigned_to = 1
        db_session.commit()

        staff = next(s for s in reports.staff_report(db_session, *PERIOD)["staff"]
                     if s["staffId"] == 1)
        assert staff["outcomeRates"]["approved"] is None

    def test_filter_by_staff_id(self, db_session):
        item = _item_with_sla(db_session)
        app = _make_application(db_session, item=item, status="processing")
        app.assigned_to = 1
        db_session.commit()

        result = reports.staff_report(db_session, *PERIOD, staff_id=1)
        assert len(result["staff"]) == 1
        assert result["staff"][0]["staffId"] == 1


class TestPeriodDefaults:
    def test_resolve_period_defaults_to_settings(self, db_session):
        start, end = reports.resolve_period(db_session, None, None)
        assert (end - start).days == 30

    @pytest.mark.parametrize("bad", ["hom-nay", "2026-13-45", "24/08/2026"])
    def test_invalid_date_rejected(self, db_session, bad):
        with pytest.raises(ValueError):
            reports.resolve_period(db_session, bad, None)

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_date_treated_as_unset(self, db_session, blank):
        """Ô ngày bị xoá trống = "không chọn", không phải giá trị sai.

        Giao diện gửi `?date_from=` khi người dùng xoá ô lọc. Trả 422 vào mặt
        họ vì đúng thao tác đó là vô lý.
        """
        start, end = reports.resolve_period(db_session, blank, None)
        assert (end - start).days == 30

    def test_end_before_start_rejected(self, db_session):
        with pytest.raises(ValueError, match="date_from"):
            reports.resolve_period(db_session, "2026-09-01", "2026-08-01")
