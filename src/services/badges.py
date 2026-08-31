"""Huy hiệu cư dân — gamification cho tiến độ nhận nhà.

Ba lựa chọn thiết kế cần biết trước khi sửa:

1. **Danh sách badge là hằng số trong code, không nằm ở DB.** Cùng lý do đã áp
   cho rule engine checklist: tất định, đọc được lúc review, không cần migration
   để sửa một dòng chữ hiển thị.

2. **Trao badge bằng INSERT ... ON CONFLICT, không phải đọc-rồi-ghi.** Hai
   request đồng thời (hai tab cùng tick một mục) đều thấy "chưa có badge" rồi
   cùng insert. `UNIQUE(user_id, badge_key)` là chốt chặn thật; hàm ở đây chỉ
   đọc số dòng ảnh hưởng để biết có trao mới hay không.

3. **Badge KHÔNG bị thu hồi.** Bỏ tick một mục không xoá huy hiệu đã đạt —
   badge ghi nhận "đã từng đạt tới đó". Thu hồi sẽ phạt cư dân vì một thao tác
   sửa nhầm.

Tiến độ tính lại bằng chính rule engine (`generate_checklist`), không tự đếm:
hai chỗ đếm sẽ lệch nhau ngay lần đầu ai đó đổi điều kiện lọc.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.models.db import UserBadge
from src.services import store
from src.services.checklist import generate_checklist

logger = logging.getLogger(__name__)

# Chép từ docs/superpowers/specs/2026-08-25-phase-2-design.md mục 12.1.
# Thứ tự ở đây là thứ tự hiển thị — giữ nguyên để giao diện không nhảy chỗ.
BADGES: tuple[dict[str, str], ...] = (
    {"key": "first_step", "name": "Bước đầu tiên", "icon": "🎯"},
    {"key": "half_way", "name": "Tiến một nửa", "icon": "📊"},
    {"key": "resident_card", "name": "Thẻ cư dân", "icon": "🏠"},
    {"key": "vehicle_card", "name": "Thẻ xe", "icon": "🚗"},
    {"key": "all_done", "name": "Hoàn tất", "icon": "🎉"},
    {"key": "fast_track", "name": "Nhanh như chớp", "icon": "⚡"},
)

BADGE_KEYS = frozenset(b["key"] for b in BADGES)

# Badge thẻ khớp theo CATEGORY của mục checklist, không theo tên hay id:
#   - tên có biến thể ("Làm thẻ cư dân (chủ hộ)" / "(người thuê)"), và
#     "Đăng ký thẻ thang máy" cũng chứa chữ "thẻ" nhưng không phải thẻ cư dân;
#   - `checklist_item_id` đổi sau mỗi lần seed vì `seed_data` xoá và tạo lại bảng.
# `seed_data.validate_badge_categories` canh cho hai chuỗi này luôn tồn tại.
CARD_BADGE_BY_CATEGORY = {
    "Giấy tờ cư dân": "resident_card",
    "Phương tiện": "vehicle_card",
}

# Mốc "nhanh" tính bằng ngày THƯỜNG, không phải ngày làm việc — đây là trải
# nghiệm của cư dân, không phải cam kết xử lý của BQL (khác với SLA trong
# `src/services/reporting.py`, cố ý).
FAST_TRACK_DAYS = 7


def award_badge(db: Session, user_id: int, badge_key: str) -> bool:
    """Trao badge. Trả True nếu vừa trao, False nếu cư dân đã có.

    Không commit — để chỗ gọi gộp vào transaction của thao tác chính.
    """
    if badge_key not in BADGE_KEYS:
        raise ValueError(f"badge_key không hợp lệ: {badge_key!r}. Chỉ có: {sorted(BADGE_KEYS)}")

    # ON CONFLICT DO NOTHING chạy được trên cả SQLite (test) lẫn Postgres.
    result = db.execute(
        text(
            "INSERT INTO user_badges (user_id, badge_key) VALUES (:user_id, :badge_key) "
            "ON CONFLICT (user_id, badge_key) DO NOTHING"
        ),
        {"user_id": user_id, "badge_key": badge_key},
    )
    db.flush()
    return result.rowcount > 0


def _visible_items(db: Session, user: dict[str, Any]) -> list[dict[str, Any]]:
    """Các mục checklist áp dụng cho cư dân này, theo đúng rule engine."""
    return generate_checklist(user, store.list_checklist_items(db))


def check_progress_badges(db: Session, user_id: int) -> list[str]:
    """Kiểm và trao các badge dựa trên tiến độ checklist.

    Gọi sau mỗi lần tick/bỏ tick. Trả về danh sách badge VỪA trao (rỗng nếu
    không có gì mới) để giao diện chạy hiệu ứng chúc mừng.
    """
    user = store.get_user(db, user_id)
    if user is None:
        return []

    items = _visible_items(db, user)
    if not items:
        return []

    done_ids = set(store.get_completions(db, user_id))
    completed = sum(1 for item in items if item["id"] in done_ids)
    total = len(items)

    earned: list[str] = []

    # So sánh dùng `>=` chứ không `==`: tổng số mục thay đổi được khi cư dân sửa
    # hồ sơ (mua xe → thêm mục), nên một người từng ở 100% có thể tụt xuống.
    if completed >= 1 and award_badge(db, user_id, "first_step"):
        earned.append("first_step")
    if completed * 2 >= total and award_badge(db, user_id, "half_way"):
        earned.append("half_way")
    if completed >= total and award_badge(db, user_id, "all_done"):
        earned.append("all_done")

    if completed >= total and _is_fast_track(user):
        if award_badge(db, user_id, "fast_track"):
            earned.append("fast_track")

    return earned


def _is_fast_track(user: dict[str, Any]) -> bool:
    """Xong toàn bộ trong vòng 7 ngày kể từ lúc hoàn thành onboarding.

    Chưa onboarding (`None`) thì không xét — không có mốc để đo, và đây không
    phải lỗi.
    """
    started = user.get("onboarding_completed_at")
    if started is None:
        return False
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    return datetime.now(UTC) - started <= timedelta(days=FAST_TRACK_DAYS)


def _la_thu_tuc_cap_the(task_name: str, badge_key: str) -> bool:
    """Thủ tục này có thật sự CẤP tấm thẻ mà badge nói tới không.

    Khớp bằng chữ trong tên, không bằng id: `seed_data` xoá và tạo lại
    `checklist_items` nên id đổi sau mỗi lần seed.

    Cố ý hẹp — thủ tục mới cùng category sẽ KHÔNG được trao badge cho tới khi
    ai đó thêm vào đây. Sai về phía không trao thì cư dân thiếu một huy hiệu;
    sai về phía trao bừa thì huy hiệu mất hết ý nghĩa.
    """
    ten = task_name.lower()
    if badge_key == "vehicle_card":
        return "thẻ xe" in ten
    if badge_key == "resident_card":
        return "thẻ cư dân" in ten
    return False


def check_card_badges(db: Session, user_id: int, checklist_item_id: int) -> list[str]:
    """Kiểm badge thẻ khi một hồ sơ được duyệt.

    Gọi từ đường đổi trạng thái hồ sơ, chỉ khi sang `approved`/`delivered`.
    """
    item = store.get_checklist_item(db, checklist_item_id)
    if item is None:
        return []

    badge_key = CARD_BADGE_BY_CATEGORY.get(item["category"])
    if badge_key is None:
        return []

    # Category là ĐIỀU KIỆN CẦN, chưa đủ. Category "Phương tiện" có HAI mục —
    # "Đăng ký thẻ xe" và "Đăng ký chỗ đỗ xe cố định" — và cả hai cùng
    # `conditions={"has_car": True}`, tức cùng hiện với một người. Chỉ khớp
    # category thì duyệt chỗ đỗ xe cũng trao badge "Thẻ xe", trong khi chính
    # thủ tục đó lại ĐÒI ảnh thẻ xe làm giấy tờ đính kèm — trao huy hiệu "đã
    # có thẻ xe" cho việc giả định thẻ xe có sẵn.
    #
    # (Cặp "Giấy tờ cư dân" không dính vì hai mục loại trừ nhau qua
    # `ownership_type`: owner và renter không bao giờ thấy cả hai.)
    #
    # Lọc thêm bằng CHỮ trong tên thủ tục thay vì id: id đổi sau mỗi lần seed.
    if not _la_thu_tuc_cap_the(item["task_name"], badge_key):
        return []

    return [badge_key] if award_badge(db, user_id, badge_key) else []


def list_user_badges(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Toàn bộ badge kèm trạng thái đạt/chưa đạt.

    Trả CẢ badge chưa đạt: giao diện hiện chúng dạng khoá để cư dân thấy còn gì
    phía trước. Thứ tự theo `BADGES`, không theo lúc đạt.
    """
    earned_at = {
        row.badge_key: row.earned_at
        for row in db.scalars(select(UserBadge).where(UserBadge.user_id == user_id))
    }
    return [
        {
            **badge,
            "earnedAt": earned_at.get(badge["key"]),
            "isEarned": badge["key"] in earned_at,
        }
        for badge in BADGES
    ]


def safe_check_progress(db: Session, user_id: int) -> list[str]:
    """`check_progress_badges` nhưng nuốt mọi lỗi.

    Dùng ở đường tick checklist: hỏng phần huy hiệu không được kéo theo thao tác
    thật của cư dân. Lỗi vẫn vào log để còn sửa.
    """
    try:
        return check_progress_badges(db, user_id)
    except Exception:
        logger.exception("badge_check_failed user_id=%s", user_id)
        return []


def safe_check_card(db: Session, user_id: int, checklist_item_id: int) -> list[str]:
    """`check_card_badges` nhưng nuốt mọi lỗi — xem `safe_check_progress`."""
    try:
        return check_card_badges(db, user_id, checklist_item_id)
    except Exception:
        logger.exception("card_badge_check_failed user_id=%s", user_id)
        return []
