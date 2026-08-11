"""Test rule engine — nơi đáng đầu tư test nhất của dự án.

Hàm thuần nên không cần mock gì. Nó bảo vệ đúng thứ tạo nên giá trị sản phẩm:
cá nhân hóa. Checklist sai cho một persona thì luận điểm sản phẩm sụp, mà lỗi
loại này rất khó phát hiện bằng mắt.
"""

import pytest

from src.services.checklist import (
    generate_checklist,
    matches,
    progress_percent,
    validate_conditions,
)

OWNER_WITH_CAR = {
    "ownership_type": "owner",
    "apartment_type": "2pn",
    "has_car": True,
    "amenity_packages": ["pool"],
}
RENTER_NO_CAR = {
    "ownership_type": "renter",
    "apartment_type": "1pn",
    "has_car": False,
    "amenity_packages": [],
}


@pytest.mark.parametrize(
    "profile,conditions,expected",
    [
        # Điều kiện rỗng áp dụng cho mọi cư dân.
        (OWNER_WITH_CAR, {}, True),
        (RENTER_NO_CAR, {}, True),
        # Khớp theo loại sở hữu — nhánh cá nhân hóa quan trọng nhất.
        (OWNER_WITH_CAR, {"ownership_type": "owner"}, True),
        (OWNER_WITH_CAR, {"ownership_type": "renter"}, False),
        (RENTER_NO_CAR, {"ownership_type": "renter"}, True),
        # Boolean.
        (OWNER_WITH_CAR, {"has_car": True}, True),
        (RENTER_NO_CAR, {"has_car": True}, False),
        # Multi-select: điều kiện mang giá trị đơn, hiểu là "nằm trong danh sách".
        (OWNER_WITH_CAR, {"amenity_packages": "pool"}, True),
        (OWNER_WITH_CAR, {"amenity_packages": "gym"}, False),
        (RENTER_NO_CAR, {"amenity_packages": "pool"}, False),
        # Nhiều điều kiện cùng lúc là phép AND.
        (OWNER_WITH_CAR, {"ownership_type": "owner", "has_car": True}, True),
        (OWNER_WITH_CAR, {"ownership_type": "owner", "has_car": False}, False),
    ],
)
def test_matches(profile: dict, conditions: dict, expected: bool) -> None:
    assert matches(profile, conditions) is expected


def test_owner_and_renter_get_different_checklists() -> None:
    """Đây chính là điều đề bài yêu cầu: checklist theo tình huống từng hộ."""
    items = [
        {"id": 1, "conditions": {}, "order_index": 1},
        {"id": 2, "conditions": {"ownership_type": "owner"}, "order_index": 2},
        {"id": 3, "conditions": {"ownership_type": "renter"}, "order_index": 3},
        {"id": 4, "conditions": {"has_car": True}, "order_index": 4},
    ]

    owner_ids = [item["id"] for item in generate_checklist(OWNER_WITH_CAR, items)]
    renter_ids = [item["id"] for item in generate_checklist(RENTER_NO_CAR, items)]

    assert owner_ids == [1, 2, 4]
    assert renter_ids == [1, 3]


def test_checklist_sorted_by_order_index() -> None:
    items = [
        {"id": 1, "conditions": {}, "order_index": 3},
        {"id": 2, "conditions": {}, "order_index": 1},
        {"id": 3, "conditions": {}, "order_index": 2},
    ]
    assert [i["id"] for i in generate_checklist(OWNER_WITH_CAR, items)] == [2, 3, 1]


def test_profile_chua_onboarding_chi_nhan_muc_chung() -> None:
    """Chưa điền form thì các thuộc tính là None, chỉ mục điều kiện rỗng khớp."""
    empty = {"ownership_type": None, "has_car": None, "amenity_packages": []}
    items = [
        {"id": 1, "conditions": {}, "order_index": 1},
        {"id": 2, "conditions": {"ownership_type": "owner"}, "order_index": 2},
    ]
    assert [i["id"] for i in generate_checklist(empty, items)] == [1]


def test_validate_conditions_bat_loi_go_nham() -> None:
    """Không có bước này thì mục gõ sai key sẽ âm thầm không hiện với ai."""
    validate_conditions({"ownership_type": "owner"})  # hợp lệ, không ném lỗi

    with pytest.raises(ValueError, match="ownership_typ"):
        validate_conditions({"ownership_typ": "owner"})


@pytest.mark.parametrize(
    "total,completed,expected",
    [(0, 0, 0), (10, 0, 0), (10, 5, 50), (10, 10, 100), (3, 1, 33)],
)
def test_progress_percent(total: int, completed: int, expected: int) -> None:
    assert progress_percent(total, completed) == expected
