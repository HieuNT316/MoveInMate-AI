"""Tests for audit logging."""
from unittest.mock import MagicMock, patch

from src.middleware.audit import log_action


class TestLogAction:
    """Unit tests for the log_action function."""

    def test_log_action_inserts_audit_record(self):
        """log_action executes INSERT with correct parameters."""
        mock_db = MagicMock()

        log_action(
            mock_db,
            user_id=1,
            action="application.status_changed",
            resource_type="application",
            resource_id=42,
            old_value={"status": "received"},
            new_value={"status": "approved"},
            ip_address="192.168.1.1",
            user_agent="TestClient/1.0",
        )

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params["user_id"] == 1
        assert params["action"] == "application.status_changed"
        assert params["resource_type"] == "application"
        assert params["resource_id"] == 42
        assert params["old_value"] == {"status": "received"}
        assert params["new_value"] == {"status": "approved"}
        assert params["ip_address"] == "192.168.1.1"
        assert params["user_agent"] == "TestClient/1.0"

    def test_log_action_with_minimal_params(self):
        """log_action works with only required parameters."""
        mock_db = MagicMock()

        log_action(
            mock_db,
            user_id=None,
            action="ticket.created",
            resource_type="ticket",
            resource_id=None,
        )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params["user_id"] is None
        assert params["resource_id"] is None
        assert params["old_value"] is None
        assert params["new_value"] is None
        assert params["ip_address"] is None
        assert params["user_agent"] is None

    def test_log_action_handles_exception(self):
        """log_action does not raise on DB error, just logs it."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("DB connection failed")

        with patch("src.middleware.audit.logger") as mock_logger:
            # Should not raise
            log_action(
                mock_db,
                user_id=1,
                action="test.action",
                resource_type="test",
                resource_id=1,
            )
            mock_logger.error.assert_called_once_with("Failed to log audit: DB connection failed")


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
