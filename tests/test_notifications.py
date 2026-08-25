"""Tests for the notifications service."""
from unittest.mock import AsyncMock, patch

import pytest

from src.services.notifications import (
    notify_application_status_change,
    notify_bql_new_application,
)


class TestNotifyApplicationStatusChange:
    """Unit tests for notify_application_status_change."""

    _base_app = {
        "user_id": 5,
        "application_id": 10,
        "checklist_item_id": 2,
        "bql_note": None,
    }

    @pytest.mark.asyncio
    async def test_received_notification(self):
        """Sends push with correct title and body for 'received' status."""
        # push is a lazy import inside the function — patch the source module.
        with patch("src.services.push.send_push_to_user", new_callable=AsyncMock) as mock_send:
            await notify_application_status_change(
                application=self._base_app,
                new_status="received",
                resident_name="Nguyễn Văn A",
                checklist_item_name="Đăng ký thẻ xe",
            )

        mock_send.assert_awaited_once_with(
            5,
            "Hồ sơ đã được gửi",
            "Hồ sơ đăng ký Đăng ký thẻ xe đang chờ BQL xử lý.",
            "/documents",
        )

    @pytest.mark.asyncio
    async def test_processing_notification(self):
        """Sends push with correct title and body for 'processing' status."""
        with patch("src.services.push.send_push_to_user", new_callable=AsyncMock) as mock_send:
            await notify_application_status_change(
                application=self._base_app,
                new_status="processing",
                resident_name="Trần Thị B",
                checklist_item_name="Làm thẻ cư dân",
            )

        mock_send.assert_awaited_once_with(
            5,
            "Hồ sơ đang được xử lý",
            "Hồ sơ của bạn đang được BQL xem xét.",
            "/documents",
        )

    @pytest.mark.asyncio
    async def test_needs_info_notification(self):
        """Sends push with correct title and body for 'needs_info' status."""
        with patch("src.services.push.send_push_to_user", new_callable=AsyncMock) as mock_send:
            await notify_application_status_change(
                application=self._base_app,
                new_status="needs_info",
                resident_name="Lê Văn C",
                checklist_item_name="Đăng ký gửi xe",
            )

        mock_send.assert_awaited_once_with(
            5,
            "Hồ sơ cần bổ sung giấy tờ",
            "Vui lòng bổ sung giấy tờ cho hồ sơ Đăng ký gửi xe.",
            "/documents",
        )

    @pytest.mark.asyncio
    async def test_approved_notification(self):
        """Sends push with correct title and body for 'approved' status."""
        with patch("src.services.push.send_push_to_user", new_callable=AsyncMock) as mock_send:
            await notify_application_status_change(
                application=self._base_app,
                new_status="approved",
                resident_name="Phạm Thị D",
                checklist_item_name="Đăng ký internet",
            )

        mock_send.assert_awaited_once_with(
            5,
            "Hồ sơ đã được duyệt!",
            "Chúc mừng! Hồ sơ Đăng ký internet đã được duyệt.",
            "/documents",
        )

    @pytest.mark.asyncio
    async def test_rejected_notification_includes_note(self):
        """Rejected status includes bql_note from application in body."""
        app_with_note = {**self._base_app, "bql_note": "Giấy tờ không hợp lệ"}

        with patch("src.services.push.send_push_to_user", new_callable=AsyncMock) as mock_send:
            await notify_application_status_change(
                application=app_with_note,
                new_status="rejected",
                resident_name="Hoàng Văn E",
                checklist_item_name="Đăng ký thẻ cư dân",
            )

        mock_send.assert_awaited_once_with(
            5,
            "Hồ sơ bị từ chối",
            "Hồ sơ Đăng ký thẻ cư dân không được duyệt."
            " Lý do: Giấy tờ không hợp lệ.",
            "/documents",
        )

    @pytest.mark.asyncio
    async def test_rejected_notification_without_note(self):
        """Rejected status uses fallback message when bql_note is absent."""
        # Pass app WITHOUT bql_note key — dict.get() returns None when key is
        # absent, but returns the None value when the key is present with None.
        app_no_note = {"user_id": 5, "application_id": 10, "checklist_item_id": 2}

        with patch("src.services.push.send_push_to_user", new_callable=AsyncMock) as mock_send:
            await notify_application_status_change(
                application=app_no_note,
                new_status="rejected",
                resident_name="Ngô Thị F",
                checklist_item_name="Đăng ký cáp quang",
            )

        mock_send.assert_awaited_once_with(
            5,
            "Hồ sơ bị từ chối",
            "Hồ sơ Đăng ký cáp quang không được duyệt."
            " Lý do: Không có ghi chú.",
            "/documents",
        )

    @pytest.mark.asyncio
    async def test_unknown_status_does_nothing(self):
        """Unknown status exits early without sending push."""
        with patch("src.services.push.send_push_to_user", new_callable=AsyncMock) as mock_send:
            await notify_application_status_change(
                application=self._base_app,
                new_status="unknown_status",
                resident_name="Test",
                checklist_item_name="Test",
            )

        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_failure_is_non_fatal(self):
        """Push failure does not raise — notification failure is non-fatal."""
        with patch("src.services.push.send_push_to_user", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = RuntimeError("network error")

            # Should not raise
            await notify_application_status_change(
                application=self._base_app,
                new_status="approved",
                resident_name="Test",
                checklist_item_name="Test",
            )

        mock_send.assert_awaited_once()


class TestNotifyBqlNewApplication:
    """Unit tests for notify_bql_new_application."""

    _base_app = {"application_id": 99, "user_id": 7}

    @pytest.mark.asyncio
    async def test_logs_bql_notification(self, caplog):
        """notify_bql_new_application logs title, body, and application_id."""
        import logging

        with caplog.at_level(logging.INFO):
            await notify_bql_new_application(
                application=self._base_app,
                resident_name="Trần Văn G",
                checklist_item_name="Làm thẻ gửi xe",
            )

        assert "Có hồ sơ mới cần xử lý" in caplog.text
        assert "Trần Văn G" in caplog.text
        assert "Làm thẻ gửi xe" in caplog.text
        assert "application_id=99" in caplog.text
