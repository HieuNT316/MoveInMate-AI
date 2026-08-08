"""Lưu trữ tạm trong bộ nhớ cho bản demo luồng.

⚠️ TẠM THỜI — sẽ được thay bằng SQLAlchemy + Supabase Postgres. Mục đích duy
nhất là chạy được luồng end-to-end mà không phải chờ dựng Supabase project.
Dữ liệu mất khi restart server.

⚠️ Nội dung checklist dưới đây là DỮ LIỆU DEMO, chưa được BQL xác nhận. Nó
đủ để thể hiện cơ chế cá nhân hóa, nhưng KHÔNG được dùng làm nguồn thông tin
thủ tục thật cho tới khi có tài liệu chính thức (cổng dữ liệu 13/08).
"""

from datetime import UTC, datetime
from typing import Any

from src.services.checklist import validate_conditions

# --- Người dùng ---------------------------------------------------------
# Tài khoản do BQL cấp; cư dân không tự đăng ký được.
# id 2 đã onboarding (demo checklist ngay), id 3 chưa (demo luồng điền form).

_USERS: dict[int, dict[str, Any]] = {
    1: {
        "user_id": 1,
        "full_name": "Ban quản lý Smart City",
        "email": "bql@smartcity.demo",
        "apartment": "-",
        "building": "-",
        "role": "admin",
        "ownership_type": None,
        "apartment_type": None,
        "has_car": None,
        "amenity_packages": [],
        "onboarding_completed_at": None,
    },
    2: {
        "user_id": 2,
        "full_name": "Trần Văn An",
        "email": "an.tran@demo.vn",
        "apartment": "S2.03-1512",
        "building": "Sapphire 2",
        "role": "resident",
        "ownership_type": "owner",
        "apartment_type": "2pn",
        "has_car": True,
        "amenity_packages": ["pool"],
        "onboarding_completed_at": datetime(2026, 8, 7, 9, 0, tzinfo=UTC),
    },
    3: {
        "user_id": 3,
        "full_name": "Lê Thị Bình",
        "email": "binh.le@demo.vn",
        "apartment": "S1.01-0803",
        "building": "Sapphire 1",
        "role": "resident",
        "ownership_type": None,
        "apartment_type": None,
        "has_car": None,
        "amenity_packages": [],
        "onboarding_completed_at": None,
    },
}

# --- Checklist template -------------------------------------------------
# `conditions` rỗng = áp dụng cho mọi cư dân.
# `item_type` = third_party_info: quy trình ngoài phạm vi BQL, không tracking
# phía BQL, nguồn hướng dẫn là quy định pháp luật công khai.

_CHECKLIST_ITEMS: list[dict[str, Any]] = [
    {
        "id": 1,
        "task_name": "Ký nội quy toà nhà",
        "description": "Đọc và ký xác nhận nội quy sử dụng căn hộ tại văn phòng BQL.",
        "category": "Thủ tục chung",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 1,
    },
    {
        "id": 2,
        "task_name": "Làm thẻ cư dân (chủ hộ)",
        "description": "Nộp CCCD và giấy tờ chứng minh quyền sở hữu căn hộ, kèm ảnh 3x4.",
        "category": "Giấy tờ cư dân",
        "conditions": {"ownership_type": "owner"},
        "item_type": "bql_actionable",
        "order_index": 2,
    },
    {
        "id": 3,
        "task_name": "Làm thẻ cư dân (người thuê)",
        "description": "Nộp CCCD, hợp đồng thuê nhà và giấy uỷ quyền của chủ hộ, kèm ảnh 3x4.",
        "category": "Giấy tờ cư dân",
        "conditions": {"ownership_type": "renter"},
        "item_type": "bql_actionable",
        "order_index": 2,
    },
    {
        "id": 4,
        "task_name": "Đăng ký tạm trú tại công an phường",
        "description": (
            "Thủ tục này do cơ quan công an xử lý, không thuộc phạm vi BQL. "
            "Hướng dẫn dựa trên quy định công khai hiện hành."
        ),
        "category": "Cư trú",
        "conditions": {"ownership_type": "renter"},
        "item_type": "third_party_info",
        "order_index": 3,
    },
    {
        "id": 5,
        "task_name": "Cập nhật thông tin cư trú",
        "description": (
            "Cập nhật nơi thường trú mới qua VNeID hoặc công an phường. "
            "Không thuộc phạm vi BQL."
        ),
        "category": "Cư trú",
        "conditions": {"ownership_type": "owner"},
        "item_type": "third_party_info",
        "order_index": 3,
    },
    {
        "id": 6,
        "task_name": "Đăng ký thẻ xe",
        "description": "Đăng ký thẻ ra vào hầm gửi xe cho ô tô hoặc xe máy.",
        "category": "Phương tiện",
        "conditions": {"has_car": True},
        "item_type": "bql_actionable",
        "order_index": 4,
    },
    {
        "id": 7,
        "task_name": "Đăng ký chỗ đỗ xe cố định",
        "description": "Đăng ký vị trí đỗ xe theo tháng tại hầm B1-B3.",
        "category": "Phương tiện",
        "conditions": {"has_car": True},
        "item_type": "bql_actionable",
        "order_index": 5,
    },
    {
        "id": 8,
        "task_name": "Kích hoạt thẻ hồ bơi",
        "description": "Kích hoạt quyền sử dụng hồ bơi theo gói tiện ích đã đăng ký.",
        "category": "Tiện ích",
        "conditions": {"amenity_packages": "pool"},
        "item_type": "bql_actionable",
        "order_index": 6,
    },
    {
        "id": 9,
        "task_name": "Kích hoạt thẻ phòng gym",
        "description": "Kích hoạt quyền sử dụng phòng gym theo gói tiện ích đã đăng ký.",
        "category": "Tiện ích",
        "conditions": {"amenity_packages": "gym"},
        "item_type": "bql_actionable",
        "order_index": 7,
    },
    {
        "id": 10,
        "task_name": "Đăng ký thẻ thang máy",
        "description": "Kích hoạt thẻ thang máy theo tầng căn hộ.",
        "category": "Thủ tục chung",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 8,
    },
    {
        "id": 11,
        "task_name": "Đăng ký internet và truyền hình",
        "description": "Chọn nhà cung cấp trong danh sách được phép lắp đặt tại toà nhà.",
        "category": "Dịch vụ",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 9,
    },
    {
        "id": 12,
        "task_name": "Đăng ký chuyển đồ vào căn hộ",
        "description": "Đặt lịch dùng thang tải hàng và đăng ký thời gian chuyển đồ.",
        "category": "Thủ tục chung",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 10,
    },
]

# --- Trạng thái thay đổi theo phiên ------------------------------------

_COMPLETIONS: dict[int, dict[int, datetime]] = {2: {1: datetime(2026, 8, 7, 10, 0, tzinfo=UTC)}}
_CHAT_HISTORY: dict[int, list[dict[str, Any]]] = {}
_next_user_id = 4
_next_chat_id = 1


def _now() -> datetime:
    return datetime.now(UTC)


def get_user(user_id: int) -> dict[str, Any] | None:
    return _USERS.get(user_id)


def list_users() -> list[dict[str, Any]]:
    return [u for u in _USERS.values() if u["role"] == "resident"]


def create_user(payload: dict[str, Any]) -> dict[str, Any]:
    """US-00 — BQL tạo tài khoản cư dân."""
    global _next_user_id
    user = {
        "user_id": _next_user_id,
        "role": "resident",
        "ownership_type": None,
        "apartment_type": None,
        "has_car": None,
        "amenity_packages": [],
        "onboarding_completed_at": None,
        **payload,
    }
    _USERS[_next_user_id] = user
    _next_user_id += 1
    return user


def save_onboarding(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Lưu hồ sơ onboarding.

    `onboarding_completed_at` chỉ ghi ở lần hoàn thành ĐẦU TIÊN. Ghi đè mỗi
    lần submit sẽ làm hỏng metric "% cư dân hoàn thành onboarding trong X ngày
    đầu" — metric đó cần mốc đầu tiên, không phải lần gần nhất.
    """
    user = _USERS[user_id]
    user.update(payload)
    if user["onboarding_completed_at"] is None:
        user["onboarding_completed_at"] = _now()
    return user


def update_profile(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Cư dân sửa hồ sơ; checklist tự cập nhật vì được lọc trực tiếp.

    `payload` chỉ chứa các field người dùng thật sự gửi lên, nên không đụng
    tới phần còn lại của hồ sơ.
    """
    _USERS[user_id].update(payload)
    return _USERS[user_id]


def list_checklist_items() -> list[dict[str, Any]]:
    return _CHECKLIST_ITEMS


def get_completions(user_id: int) -> dict[int, datetime]:
    return _COMPLETIONS.setdefault(user_id, {})


def set_completion(user_id: int, item_id: int, completed: bool) -> None:
    done = _COMPLETIONS.setdefault(user_id, {})
    if completed:
        done[item_id] = _now()
    else:
        done.pop(item_id, None)


def add_chat(user_id: int, entry: dict[str, Any]) -> dict[str, Any]:
    global _next_chat_id
    record = {"id": _next_chat_id, "created_at": _now(), **entry}
    _CHAT_HISTORY.setdefault(user_id, []).append(record)
    _next_chat_id += 1
    return record


def list_chat(user_id: int) -> list[dict[str, Any]]:
    return _CHAT_HISTORY.get(user_id, [])


# Kiểm tra ngay lúc import: điều kiện seed phải dùng đúng tên field hồ sơ.
for _item in _CHECKLIST_ITEMS:
    validate_conditions(_item["conditions"])
