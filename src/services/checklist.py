"""Rule engine sinh checklist cá nhân hóa.

Hàm thuần, không đụng DB và không phụ thuộc LangGraph — vì vậy test được
độc lập, không cần mock. Đây là lựa chọn có chủ đích: phân loại cư dân dựa
trên tập hữu hạn thuộc tính thu qua form có cấu trúc, dùng LLM ở đây vừa tốn
kém vừa kém tin cậy hơn.

Cách khớp: AND trên mọi cặp key-value của `conditions`. `conditions` rỗng
nghĩa là mục áp dụng cho mọi cư dân. Không hỗ trợ OR hay so sánh khoảng —
nếu cần OR thì thêm hai dòng dữ liệu, đừng làm engine phức tạp hơn.
"""

from typing import Any

# Các field của hồ sơ cư dân được phép dùng làm điều kiện lọc.
PROFILE_FIELDS = frozenset(
    {"ownership_type", "apartment_type", "has_car", "amenity_packages"}
)


def validate_conditions(conditions: dict[str, Any]) -> None:
    """Chặn key sai chính tả khi seed dữ liệu.

    Không có bước này thì `{"ownership_typ": "owner"}` sẽ khiến mục đó âm thầm
    không bao giờ hiện với ai, mà không báo lỗi gì.
    """
    unknown = set(conditions) - PROFILE_FIELDS
    if unknown:
        raise ValueError(
            f"Điều kiện chứa field không hợp lệ: {sorted(unknown)}. "
            f"Chỉ được dùng: {sorted(PROFILE_FIELDS)}"
        )


def matches(profile: dict[str, Any], conditions: dict[str, Any]) -> bool:
    """Hồ sơ có thoả mãn toàn bộ điều kiện của một mục checklist không.

    Với field dạng danh sách (vd. `amenity_packages`), điều kiện mang giá trị
    đơn và được hiểu là "nằm trong danh sách đã chọn".
    """
    for key, expected in conditions.items():
        actual = profile.get(key)
        if isinstance(actual, list):
            if expected not in actual:
                return False
        elif actual != expected:
            return False
    return True


def generate_checklist(
    profile: dict[str, Any], items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Lọc danh sách mục theo hồ sơ, giữ thứ tự hiển thị."""
    selected = [item for item in items if matches(profile, item["conditions"])]
    return sorted(selected, key=lambda item: item["order_index"])


def progress_percent(total: int, completed: int) -> int:
    """Phần trăm hoàn thành, làm tròn xuống. Không có mục nào thì coi là 0%."""
    if total <= 0:
        return 0
    return int(completed * 100 / total)


def summarize_progress(
    items: list[dict[str, Any]], completed_ids: set[int]
) -> dict[str, int]:
    """Tổng hợp tiến độ cho một tập mục."""
    total = len(items)
    completed = sum(1 for item in items if item["id"] in completed_ids)
    return {
        "total": total,
        "completed": completed,
        "percent": progress_percent(total, completed),
    }


def only_bql_scope(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lọc ra các mục BQL thật sự xử lý được.

    Dùng cho dashboard BQL và cho eval tỉ lệ hoàn tất. Trộn chung với thủ tục
    ở cơ quan bên ngoài sẽ khiến BQL thấy cư dân "chậm" vì việc mà chính BQL
    không giúp được và cũng không có cách nào xác nhận.
    """
    return [item for item in items if item["item_type"] == "bql_actionable"]
