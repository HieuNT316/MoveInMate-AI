"""Test hệ huy hiệu.

Badge là tính năng phụ, nhưng nó móc vào hai đường ghi chính (tick checklist và
duyệt hồ sơ) nên lỗi ở đây làm hỏng thứ quan trọng hơn nó. Phần lớn test dưới
đây canh đúng chỗ đó: trao trùng, thu hồi ngoài ý muốn, và lỗi lan ra request.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from src.models.db import ChecklistCompletion, User, UserBadge
from src.services import badges, store


def _award_all_checklist_items(db, user_id: int) -> None:
    """Tick mọi mục checklist áp dụng cho một cư dân."""
    user = store.get_user(db, user_id)
    items = badges._visible_items(db, user)
    for item in items:
        db.add(ChecklistCompletion(user_id=user_id, checklist_item_id=item["id"]))
    db.commit()


class TestAwardBadge:
    def test_awards_once(self, db_session):
        assert badges.award_badge(db_session, 2, "first_step") is True

    def test_second_award_is_noop(self, db_session):
        """Gọi hai lần chỉ trao một — chốt chặn nằm ở UNIQUE của DB.

        Đây là ca race condition thật: hai tab cùng tick một mục, cả hai đều
        đọc thấy "chưa có badge" rồi cùng insert.
        """
        assert badges.award_badge(db_session, 2, "first_step") is True
        assert badges.award_badge(db_session, 2, "first_step") is False

        rows = db_session.scalars(
            select(UserBadge).where(UserBadge.user_id == 2, UserBadge.badge_key == "first_step")
        ).all()
        assert len(rows) == 1

    def test_different_users_independent(self, db_session):
        assert badges.award_badge(db_session, 2, "first_step") is True
        assert badges.award_badge(db_session, 3, "first_step") is True

    def test_unknown_badge_key_rejected(self, db_session):
        """Gõ sai khoá badge phải nổ ngay lúc gọi, không im lặng ghi rác.

        Cùng lý do với `validate_conditions`: một khoá sai chính tả sẽ nằm im
        trong DB và không bao giờ khớp danh sách hiển thị.
        """
        with pytest.raises(ValueError, match="badge_key"):
            badges.award_badge(db_session, 2, "khong_ton_tai")


class TestProgressBadges:
    def test_first_step_on_first_completion(self, db_session):
        # conftest đã tick sẵn mục 1 cho user 2.
        awarded = badges.check_progress_badges(db_session, 2)
        assert "first_step" in awarded

    def test_no_badge_without_completion(self, db_session):
        """User 3 chưa tick gì — không được có badge nào."""
        assert badges.check_progress_badges(db_session, 3) == []

    def test_all_done_and_half_way_when_complete(self, db_session):
        _award_all_checklist_items(db_session, 5)
        awarded = badges.check_progress_badges(db_session, 5)
        assert "all_done" in awarded
        assert "half_way" in awarded
        assert "first_step" in awarded

    def test_repeat_call_awards_nothing_new(self, db_session):
        _award_all_checklist_items(db_session, 5)
        badges.check_progress_badges(db_session, 5)
        assert badges.check_progress_badges(db_session, 5) == []

    def test_untick_does_not_revoke(self, db_session):
        """Bỏ tick KHÔNG thu hồi badge — badge ghi nhận 'đã từng đạt'.

        Quyết định có chủ ý (spec mục 4.5): thu hồi sẽ khiến cư dân sửa nhầm
        một ô rồi mất huy hiệu, một hình phạt không tương xứng.
        """
        _award_all_checklist_items(db_session, 5)
        badges.check_progress_badges(db_session, 5)

        db_session.query(ChecklistCompletion).filter_by(user_id=5).delete()
        db_session.commit()
        badges.check_progress_badges(db_session, 5)

        earned = {b["key"] for b in badges.list_user_badges(db_session, 5) if b["isEarned"]}
        assert "all_done" in earned

    def test_fast_track_within_seven_days(self, db_session):
        """Xong 100% trong vòng 7 ngày kể từ lúc onboarding."""
        user = db_session.get(User, 5)
        user.onboarding_completed_at = datetime.now(UTC) - timedelta(days=3)
        db_session.commit()

        _award_all_checklist_items(db_session, 5)
        assert "fast_track" in badges.check_progress_badges(db_session, 5)

    def test_fast_track_not_awarded_after_seven_days(self, db_session):
        user = db_session.get(User, 5)
        user.onboarding_completed_at = datetime.now(UTC) - timedelta(days=30)
        db_session.commit()

        _award_all_checklist_items(db_session, 5)
        assert "fast_track" not in badges.check_progress_badges(db_session, 5)

    def test_fast_track_skipped_when_onboarding_null(self, db_session):
        """Chưa onboarding thì không xét fast_track, và KHÔNG lỗi."""
        user = db_session.get(User, 5)
        user.onboarding_completed_at = None
        db_session.commit()

        _award_all_checklist_items(db_session, 5)
        awarded = badges.check_progress_badges(db_session, 5)
        assert "all_done" in awarded
        assert "fast_track" not in awarded

    def test_unknown_user_returns_empty(self, db_session):
        """User không tồn tại → rỗng, không ném lỗi lên request đang chạy."""
        assert badges.check_progress_badges(db_session, 999) == []


class TestCardBadges:
    def test_resident_card_badge(self, db_session):
        """Mục thuộc category 'Giấy tờ cư dân' được duyệt → badge thẻ cư dân."""
        item = next(
            i for i in store.list_checklist_items(db_session) if i["category"] == "Giấy tờ cư dân"
        )
        assert badges.check_card_badges(db_session, 2, item["id"]) == ["resident_card"]

    def test_vehicle_card_badge(self, db_session):
        item = next(
            i for i in store.list_checklist_items(db_session) if i["category"] == "Phương tiện"
        )
        assert badges.check_card_badges(db_session, 2, item["id"]) == ["vehicle_card"]

    def test_other_category_awards_nothing(self, db_session):
        """'Đăng ký thẻ thang máy' có chữ 'thẻ' trong tên nhưng KHÔNG phải thẻ
        cư dân hay thẻ xe. Đây là ca mà cách khớp theo tên đã sai."""
        item = next(
            i
            for i in store.list_checklist_items(db_session)
            if i["task_name"] == "Đăng ký thẻ thang máy"
        )
        assert badges.check_card_badges(db_session, 2, item["id"]) == []

    def test_unknown_item_returns_empty(self, db_session):
        assert badges.check_card_badges(db_session, 2, 9999) == []

    def test_repeat_approval_awards_once(self, db_session):
        item = next(
            i for i in store.list_checklist_items(db_session) if i["category"] == "Phương tiện"
        )
        assert badges.check_card_badges(db_session, 2, item["id"]) == ["vehicle_card"]
        assert badges.check_card_badges(db_session, 2, item["id"]) == []


class TestListUserBadges:
    def test_lists_all_badges_including_unearned(self, db_session):
        result = badges.list_user_badges(db_session, 3)
        assert len(result) == len(badges.BADGES)
        assert all(b["isEarned"] is False for b in result)
        assert all(b["earnedAt"] is None for b in result)

    def test_earned_badge_has_timestamp(self, db_session):
        badges.award_badge(db_session, 2, "first_step")
        result = badges.list_user_badges(db_session, 2)

        first_step = next(b for b in result if b["key"] == "first_step")
        assert first_step["isEarned"] is True
        assert first_step["earnedAt"] is not None

    def test_order_is_stable(self, db_session):
        """Thứ tự theo BADGES, không theo lúc đạt — giao diện không nhảy chỗ."""
        badges.award_badge(db_session, 2, "all_done")
        badges.award_badge(db_session, 2, "first_step")

        keys = [b["key"] for b in badges.list_user_badges(db_session, 2)]
        assert keys == [b["key"] for b in badges.BADGES]


class TestSafeCheck:
    def test_swallows_errors(self, db_session, monkeypatch):
        """Lỗi badge KHÔNG được làm hỏng request chính.

        Tick checklist thất bại vì lỗi gamification là đánh đổi sai: cư dân mất
        thao tác thật để đổi lấy một huy hiệu.
        """

        def boom(*args, **kwargs):
            raise RuntimeError("DB nổ")

        monkeypatch.setattr(badges, "check_progress_badges", boom)
        assert badges.safe_check_progress(db_session, 2) == []
