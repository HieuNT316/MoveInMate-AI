"""Tests for the ticket system API."""
from unittest.mock import MagicMock, patch

import pytest

from src.services.store import (
    add_ticket_message,
    assign_ticket,
    create_ticket,
    get_all_tickets,
    get_ticket_by_id,
    get_ticket_with_messages,
    get_user_tickets,
    resolve_ticket,
    update_ticket_status,
)


class TestStoreMethods:
    """Unit tests for ticket store functions.

    `text` is imported inside the function body, so patch sqlalchemy.text.
    """

    def test_create_ticket(self):
        """Create ticket returns ticket dict with all fields."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.one.return_value._mapping = {
            "ticket_id": 1,
            "user_id": 2,
            "subject": "Test ticket",
            "status": "open",
            "priority": "normal",
            "assigned_to": None,
            "created_at": "2026-08-25T10:00:00",
        }
        mock_db.execute.return_value = mock_result

        with patch("sqlalchemy.text"):
            result = create_ticket(
                mock_db,
                user_id=2,
                subject="Test ticket",
                initial_message=None,
            )

        assert result["ticket_id"] == 1
        assert result["subject"] == "Test ticket"
        assert result["status"] == "open"
        mock_db.commit.assert_called_once()

    def test_create_ticket_with_initial_message(self):
        """Create ticket with initial message calls add_ticket_message."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.one.return_value._mapping = {
            "ticket_id": 1,
            "user_id": 2,
            "subject": "Test ticket",
            "status": "open",
            "priority": "normal",
            "assigned_to": None,
            "created_at": "2026-08-25T10:00:00",
        }
        mock_db.execute.return_value = mock_result

        with patch("sqlalchemy.text"):
            with patch("src.services.store.add_ticket_message") as mock_add:
                result = create_ticket(
                    mock_db,
                    user_id=2,
                    subject="Test ticket",
                    initial_message="This is the initial message",
                )

        assert result["ticket_id"] == 1
        mock_add.assert_called_once_with(mock_db, 1, 2, "resident", "This is the initial message")

    def test_add_ticket_message(self):
        """Add message returns message dict."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.one.return_value._mapping = {
            "message_id": 1,
            "ticket_id": 5,
            "sender_id": 2,
            "sender_type": "resident",
            "message": "Hello, I need help",
            "created_at": "2026-08-25T10:30:00",
        }
        mock_db.execute.return_value = mock_result

        with patch("sqlalchemy.text"):
            result = add_ticket_message(
                mock_db,
                ticket_id=5,
                sender_id=2,
                sender_type="resident",
                message="Hello, I need help",
            )

        assert result["message_id"] == 1
        assert result["ticket_id"] == 5
        assert result["message"] == "Hello, I need help"
        mock_db.commit.assert_called_once()

    def test_get_user_tickets(self):
        """Get user tickets returns list of ticket dicts."""
        mock_db = MagicMock()
        mock_row1 = MagicMock()
        mock_row1._mapping = {
            "ticket_id": 1,
            "user_id": 2,
            "subject": "First ticket",
            "status": "open",
            "last_message": "Need help",
        }
        mock_row2 = MagicMock()
        mock_row2._mapping = {
            "ticket_id": 2,
            "user_id": 2,
            "subject": "Second ticket",
            "status": "resolved",
            "last_message": "Issue resolved",
        }
        mock_db.execute.return_value = MagicMock(fetchall=MagicMock(return_value=[mock_row1, mock_row2]))

        with patch("sqlalchemy.text"):
            result = get_user_tickets(mock_db, user_id=2)

        assert len(result) == 2
        assert result[0]["ticket_id"] == 1
        assert result[1]["ticket_id"] == 2
        assert result[0]["last_message"] == "Need help"

    def test_get_user_tickets_empty(self):
        """Get user tickets returns empty list when none exist."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock(fetchall=MagicMock(return_value=[]))

        with patch("sqlalchemy.text"):
            result = get_user_tickets(mock_db, user_id=99)

        assert result == []

    def test_get_ticket_with_messages_found(self):
        """Get ticket with messages returns ticket and messages."""
        mock_db = MagicMock()
        mock_ticket_row = MagicMock()
        mock_ticket_row._mapping = {
            "ticket_id": 1,
            "user_id": 2,
            "subject": "Test ticket",
            "status": "open",
            "priority": "normal",
            "assigned_to_name": "Staff Member",
        }
        mock_msg_row = MagicMock()
        mock_msg_row._mapping = {
            "message_id": 1,
            "ticket_id": 1,
            "sender_id": 2,
            "sender_type": "resident",
            "message": "Help me",
            "sender_name": "Trần Văn An",
        }
        mock_db.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=mock_ticket_row)),
            MagicMock(fetchall=MagicMock(return_value=[mock_msg_row])),
        ]

        with patch("sqlalchemy.text"):
            result = get_ticket_with_messages(mock_db, ticket_id=1, user_id=2)

        assert result["ticket_id"] == 1
        assert len(result["messages"]) == 1
        assert result["messages"][0]["message"] == "Help me"

    def test_get_ticket_with_messages_not_found(self):
        """Get ticket with messages returns None when not found."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock(fetchone=MagicMock(return_value=None))

        with patch("sqlalchemy.text"):
            result = get_ticket_with_messages(mock_db, ticket_id=999, user_id=2)

        assert result is None

    def test_get_ticket_by_id(self):
        """Get ticket by ID returns ticket with user info."""
        mock_db = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {
            "ticket_id": 1,
            "user_id": 2,
            "subject": "Test ticket",
            "status": "open",
            "user_name": "Trần Văn An",
            "assigned_to_name": "Staff Member",
        }
        mock_db.execute.return_value = MagicMock(fetchone=MagicMock(return_value=mock_row))

        with patch("sqlalchemy.text"):
            result = get_ticket_by_id(mock_db, ticket_id=1)

        assert result["ticket_id"] == 1
        assert result["user_name"] == "Trần Văn An"

    def test_get_ticket_by_id_not_found(self):
        """Get ticket by ID returns None when not found."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock(fetchone=MagicMock(return_value=None))

        with patch("sqlalchemy.text"):
            result = get_ticket_by_id(mock_db, ticket_id=999)

        assert result is None

    def test_assign_ticket(self):
        """Assign ticket returns updated ticket."""
        mock_db = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {
            "ticket_id": 1,
            "user_id": 2,
            "subject": "Test ticket",
            "status": "in_progress",
            "assigned_to": 3,
        }
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        with patch("src.services.store.text"):
            result = assign_ticket(mock_db, ticket_id=1, assigned_to=3)

        assert result["assigned_to"] == 3
        assert result["status"] == "in_progress"
        mock_db.commit.assert_called_once()

    def test_assign_ticket_not_found(self):
        """Assign ticket returns None when ticket not found."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("src.services.store.text"):
            result = assign_ticket(mock_db, ticket_id=999, assigned_to=3)

        assert result is None

    def test_resolve_ticket(self):
        """Resolve ticket returns updated ticket with resolved_at."""
        mock_db = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {
            "ticket_id": 1,
            "status": "resolved",
            "resolved_at": "2026-08-25T12:00:00",
        }
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        with patch("src.services.store.text"):
            result = resolve_ticket(mock_db, ticket_id=1)

        assert result["status"] == "resolved"
        assert "resolved_at" in result
        mock_db.commit.assert_called_once()

    def test_resolve_ticket_not_found(self):
        """Resolve ticket returns None when ticket not found."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("src.services.store.text"):
            result = resolve_ticket(mock_db, ticket_id=999)

        assert result is None

    def test_update_ticket_status(self):
        """Update ticket status returns updated ticket."""
        mock_db = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {
            "ticket_id": 1,
            "status": "closed",
        }
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        with patch("src.services.store.text"):
            result = update_ticket_status(mock_db, ticket_id=1, status="closed")

        assert result["status"] == "closed"
        mock_db.commit.assert_called_once()

    def test_update_ticket_status_not_found(self):
        """Update ticket status returns None when ticket not found."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("src.services.store.text"):
            result = update_ticket_status(mock_db, ticket_id=999, status="closed")

        assert result is None

    def test_get_all_tickets(self):
        """Get all tickets returns list with optional filters."""
        mock_db = MagicMock()
        mock_row1 = MagicMock()
        mock_row1._mapping = {
            "ticket_id": 1,
            "user_id": 2,
            "subject": "Ticket 1",
            "status": "open",
            "user_name": "User A",
            "assigned_to_name": None,
        }
        mock_row2 = MagicMock()
        mock_row2._mapping = {
            "ticket_id": 2,
            "user_id": 3,
            "subject": "Ticket 2",
            "status": "in_progress",
            "user_name": "User B",
            "assigned_to_name": "Staff",
        }
        mock_db.execute.return_value = MagicMock(fetchall=MagicMock(return_value=[mock_row1, mock_row2]))

        with patch("sqlalchemy.text"):
            result = get_all_tickets(mock_db, status=None, assigned_to=None)

        assert len(result) == 2
        assert result[0]["ticket_id"] == 1
        assert result[1]["user_name"] == "User B"

    def test_get_all_tickets_with_status_filter(self):
        """Get all tickets filters by status."""
        mock_db = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {
            "ticket_id": 1,
            "user_id": 2,
            "subject": "Open ticket",
            "status": "open",
            "user_name": "User A",
            "assigned_to_name": None,
        }
        mock_db.execute.return_value = MagicMock(fetchall=MagicMock(return_value=[mock_row]))

        with patch("sqlalchemy.text"):
            result = get_all_tickets(mock_db, status="open", assigned_to=None)

        assert len(result) == 1
        assert result[0]["status"] == "open"

    def test_get_all_tickets_empty(self):
        """Get all tickets returns empty list when none exist."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock(fetchall=MagicMock(return_value=[]))

        with patch("sqlalchemy.text"):
            result = get_all_tickets(mock_db, status=None, assigned_to=None)

        assert result == []
