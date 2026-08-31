"""Tests for audit logging."""
from unittest.mock import MagicMock, patch

from src.middleware.audit import log_action


class TestLogAction:
    """Unit tests for the log_action function."""

    def test_khong_nem_loi_khi_db_hong(self):
        """Lỗi ghi nhật ký không được làm hỏng thao tác chính.

        Test này CỐ Ý dùng mock: nó kiểm hành vi nuốt lỗi, không kiểm việc ghi
        được xuống DB — phần đó thuộc `TestLogActionGhiThatXuongDB` bên dưới,
        chạy trên DB thật.

        Ba test cũ ở đây khoá `db.execute()` cùng dict tham số, tức là khoá
        CÁCH CÀI ĐẶT (raw SQL) chứ không phải hành vi. Chúng vẫn xanh suốt
        thời gian `log_action` không ghi nổi một dòng nào — xem docstring của
        `TestLogActionGhiThatXuongDB`.
        """
        mock_db = MagicMock()
        mock_db.add.side_effect = Exception("DB connection failed")

        with patch("src.middleware.audit.logger") as mock_logger:
            log_action(  # không được ném
                mock_db,
                user_id=1,
                action="test.action",
                resource_type="test",
                resource_id=1,
            )
            mock_logger.error.assert_called_once_with(
                "Failed to log audit: DB connection failed"
            )


class TestAuditInStoreFunctions:
    """Integration-style tests verifying audit logging is called from store functions."""

    def test_update_application_status_logs_audit(self):
        """update_application_status calls log_action with old and new status."""
        from src.services.store import update_application_status

        mock_db = MagicMock()
        mock_app = MagicMock()
        mock_app.application_id = 1
        mock_app.status = "received"
        mock_app.version = 1
        mock_db.scalar.return_value = mock_app

        with patch("src.services.store.log_action") as mock_log:
            update_application_status(
                mock_db,
                application_id=1,
                status="approved",
                bql_note=None,
                form_data=None,
            )

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args
            # positional: db, then kwargs
            assert call_kwargs[0][0] is mock_db  # db
            # keyword or positional
            args, kwargs = call_kwargs
            if kwargs:
                assert kwargs["action"] == "application.status_changed"
                assert kwargs["resource_type"] == "application"
                assert kwargs["resource_id"] == 1
                assert kwargs["old_value"] == {"status": "received"}
                assert kwargs["new_value"] == {"status": "approved"}
            else:
                # positional args
                assert args[2] == "application.status_changed"
                assert args[3] == "application"
                assert args[4] == 1

    def test_update_ticket_status_logs_audit(self):
        """update_ticket_status calls log_action with old and new status."""
        from src.services.store import update_ticket_status

        mock_db = MagicMock()
        # Mock old status query
        mock_old_result = MagicMock()
        mock_old_result.fetchone.return_value = MagicMock(_mapping={"status": "open"})
        mock_db.execute.return_value = mock_old_result

        with patch("src.services.store.log_action") as mock_log:
            update_ticket_status(mock_db, ticket_id=5, status="closed")

            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert kwargs["action"] == "ticket.status_changed"
            assert kwargs["resource_type"] == "ticket"
            assert kwargs["resource_id"] == 5
            assert kwargs["old_value"] == {"status": "open"}
            assert kwargs["new_value"] == {"status": "closed"}

    def test_update_ticket_status_not_found(self):
        """update_ticket_status returns None when ticket not found."""
        from src.services.store import update_ticket_status

        mock_db = MagicMock()
        mock_old_result = MagicMock()
        mock_old_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_old_result

        with patch("src.services.store.log_action") as mock_log:
            result = update_ticket_status(mock_db, ticket_id=999, status="closed")

        assert result is None
        mock_log.assert_not_called()

    def test_create_ticket_logs_audit(self):
        """create_ticket calls log_action after inserting."""
        from src.services.store import create_ticket

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.one.return_value._mapping = {
            "ticket_id": 10,
            "user_id": 2,
            "subject": "Help needed",
            "status": "open",
            "priority": "normal",
            "assigned_to": None,
            "created_at": "2026-08-25T10:00:00",
        }
        mock_db.execute.return_value = mock_result

        with patch("src.services.store.text"):
            with patch("src.services.store.log_action") as mock_log:
                result = create_ticket(
                    mock_db,
                    user_id=2,
                    subject="Help needed",
                    initial_message=None,
                )

        assert result["ticket_id"] == 10
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert kwargs["action"] == "ticket.created"
        assert kwargs["resource_type"] == "ticket"
        assert kwargs["resource_id"] == 10
        assert kwargs["user_id"] == 2
        assert kwargs["new_value"] == {"subject": "Help needed", "status": "open"}


class TestLogActionGhiThatXuongDB:
    """Chạy `log_action` trên DB THẬT, không mock.

    Các test ở trên dùng `MagicMock` cho session — mock nuốt mọi kiểu tham số
    nên chúng KHÔNG THỂ ĐỎ khi giá trị không bind được xuống DB. Đúng lỗi đã
    xảy ra: bản cũ dùng `text()` với tham số bind là `dict`, cả psycopg2 lẫn
    sqlite3 đều báo "can't adapt type 'dict'", lỗi bị `except` nuốt, và bảng
    `audit_log` rỗng hoàn toàn suốt nhiều ngày mà 610 test vẫn xanh.

    Hệ quả không chỉ là mất vết bảo mật: `_first_reached` trong
    `src/services/reports.py` đọc chính bảng này để biết hồ sơ vào trạng thái
    nào lúc nào, nên `onTimeRate` và `avgProcessingDays` trả None vĩnh viễn.
    """

    def test_ghi_duoc_dict_vao_old_value_va_new_value(self, db_session):
        """dict phải xuống được DB và đọc lại nguyên vẹn."""
        from sqlalchemy import select

        from src.models.db import AuditLog

        log_action(
            db_session,
            user_id=None,
            action="application.status_changed",
            resource_type="application",
            resource_id=7,
            old_value={"status": "received"},
            new_value={"status": "approved"},
        )
        db_session.commit()

        row = db_session.scalar(
            select(AuditLog).where(AuditLog.action == "application.status_changed")
        )
        assert row is not None, "log_action không ghi được dòng nào xuống DB"
        assert row.old_value == {"status": "received"}
        assert row.new_value == {"status": "approved"}
        assert row.resource_id == 7

    def test_ghi_duoc_khi_old_value_rong(self, db_session):
        """Hành động tạo mới không có trạng thái cũ — None phải hợp lệ."""
        from sqlalchemy import select

        from src.models.db import AuditLog

        log_action(
            db_session,
            user_id=None,
            action="ticket.created",
            resource_type="ticket",
            resource_id=3,
            old_value=None,
            new_value={"subject": "Hỏi về thẻ xe", "status": "open"},
        )
        db_session.commit()

        row = db_session.scalar(select(AuditLog).where(AuditLog.action == "ticket.created"))
        assert row is not None
        assert row.old_value is None
        assert row.new_value["subject"] == "Hỏi về thẻ xe"
