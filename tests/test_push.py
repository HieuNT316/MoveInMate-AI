"""Tests for push notification service and endpoints."""
from unittest.mock import MagicMock, patch

import pytest

from src.services.push import (
    PushError,
    SubscriptionExpired,
    delete_push_subscription,
    get_user_push_subscriptions,
    subscribe_user,
    unsubscribe_user,
    upsert_push_subscription,
)


class TestStoreMethods:
    """Unit tests for store-level push functions (no async, no web-push).

    `text` is imported inside the function body, so patch sqlalchemy.text.
    """

    def test_upsert_push_subscription(self):
        """Upsert returns subscription_id."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result

        with patch("sqlalchemy.text"):
            result = upsert_push_subscription(
                mock_db,
                user_id=1,
                endpoint="https://fcm.googleapis.com/test",
                p256dh="p256dh_value",
                auth="auth_value",
                user_agent="TestAgent/1.0",
            )

        assert result["subscription_id"] == 42
        mock_db.commit.assert_called_once()

    def test_upsert_push_subscription_with_null_user_agent(self):
        """Upsert works when user_agent is None."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result

        with patch("sqlalchemy.text"):
            result = upsert_push_subscription(
                mock_db,
                user_id=1,
                endpoint="https://fcm.googleapis.com/test",
                p256dh="p256dh_value",
                auth="auth_value",
            )

        assert result["subscription_id"] == 1

    def test_delete_push_subscription_found(self):
        """Delete returns True when subscription existed."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock(rowcount=1)

        with patch("sqlalchemy.text"):
            result = delete_push_subscription(mock_db, user_id=1, endpoint="https://fcm.googleapis.com/test")

        assert result is True
        mock_db.commit.assert_called_once()

    def test_delete_push_subscription_not_found(self):
        """Delete returns False when subscription did not exist."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock(rowcount=0)

        with patch("sqlalchemy.text"):
            result = delete_push_subscription(mock_db, user_id=1, endpoint="https://fcm.googleapis.com/test")

        assert result is False

    def test_get_user_push_subscriptions(self):
        """Get subscriptions returns list of dicts."""
        mock_db = MagicMock()
        mock_row1 = MagicMock()
        mock_row1._mapping = {"subscription_id": 1, "endpoint": "https://fcm1.test", "p256dh": "k1", "auth": "a1"}
        mock_row2 = MagicMock()
        mock_row2._mapping = {"subscription_id": 2, "endpoint": "https://fcm2.test", "p256dh": "k2", "auth": "a2"}
        mock_db.execute.return_value = MagicMock(fetchall=MagicMock(return_value=[mock_row1, mock_row2]))

        with patch("sqlalchemy.text"):
            result = get_user_push_subscriptions(mock_db, user_id=1)

        assert len(result) == 2
        assert result[0]["subscription_id"] == 1
        assert result[1]["endpoint"] == "https://fcm2.test"

    def test_get_user_push_subscriptions_empty(self):
        """Get subscriptions returns empty list when none exist."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock(fetchall=MagicMock(return_value=[]))

        with patch("sqlalchemy.text"):
            result = get_user_push_subscriptions(mock_db, user_id=99)

        assert result == []


class TestAsyncServiceFunctions:
    """Tests for async functions that open/close their own sessions.

    SessionLocal is imported inside the function body from src.database,
    so patch the source module.
    """

    @pytest.mark.asyncio
    async def test_subscribe_user(self):
        """subscribe_user calls store and returns result."""
        with patch("src.database.SessionLocal") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session

            with patch("src.services.push.upsert_push_subscription") as mock_store_fn:
                mock_store_fn.return_value = {"subscription_id": 7}

                result = await subscribe_user(
                    user_id=1,
                    endpoint="https://fcm.googleapis.com/test",
                    p256dh="p256dh_value",
                    auth="auth_value",
                )

        assert result["subscription_id"] == 7
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_user(self):
        """unsubscribe_user calls store and returns result."""
        with patch("src.database.SessionLocal") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session

            with patch("src.services.push.delete_push_subscription") as mock_store_fn:
                mock_store_fn.return_value = True

                result = await unsubscribe_user(1, "https://fcm.googleapis.com/test")

        assert result is True
        mock_session.close.assert_called_once()


class TestPushDisabled:
    """Test behavior when VAPID keys are not configured."""

    def test_init_webpush_returns_none_when_no_keys(self):
        """_init_webpush returns None when VAPID keys are empty."""
        from src.services.push import _init_webpush

        with patch("src.services.push.get_settings") as mock_settings:
            mock_settings.return_value.has_vapid_keys = False

            result = _init_webpush()
            assert result is None

    def test_init_webpush_returns_none_when_webpush_not_installed(self):
        """_init_webpush returns None when web-push library is not installed.

        `_webpush` module variable is set to None initially, triggering a lazy
        import attempt. If the import fails (library not installed), `_get_webpush`
        returns None and `_init_webpush` logs a warning.
        """
        import src.services.push as push_module

        # Reset the cache so _get_webpush will attempt a fresh import
        push_module._webpush = None

        with patch("src.services.push.get_settings") as mock_settings:
            mock_settings.return_value.has_vapid_keys = True

            # Patch _get_webpush directly to simulate import failure
            with patch.object(push_module, "_get_webpush", return_value=None):
                result = push_module._init_webpush()
                assert result is None


class TestExceptions:
    """Test custom exceptions."""

    def test_push_error_is_exception(self):
        """PushError is a subclass of Exception."""
        assert issubclass(PushError, Exception)

    def test_subscription_expired_is_push_error(self):
        """SubscriptionExpired is a subclass of PushError."""
        assert issubclass(SubscriptionExpired, PushError)

    def test_push_error_message(self):
        """PushError carries message."""
        err = PushError("test message")
        assert str(err) == "test message"

    def test_subscription_expired_message(self):
        """SubscriptionExpired carries message."""
        err = SubscriptionExpired("expired subscription")
        assert str(err) == "expired subscription"
