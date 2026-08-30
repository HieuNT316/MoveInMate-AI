"""Cấu hình hệ thống BQL sửa được lúc chạy.

Tên file là `settings_store` chứ không phải `settings` để khỏi lẫn với
`src/config.py` — hai thứ khác nhau về bản chất:

  src/config.py    — biến môi trường, đặt lúc deploy, BQL KHÔNG sửa được.
  file này         — cấu hình vận hành, BQL sửa qua giao diện.

**Chỉ lưu phần ĐÃ BỊ ĐỔI.** Mặc định nằm ở `DEFAULTS` dưới đây; DB rỗng vẫn đọc
ra đủ khoá. Ghi cả mặc định xuống DB sẽ khiến sửa mặc định trong code không có
tác dụng với môi trường đã chạy — một thay đổi tưởng là có hiệu lực nhưng không.

**Chỉ khai khoá đã có nơi tiêu thụ.** Một khoá không ai đọc là cấu hình chết:
BQL sửa, thấy 200 OK, và tin rằng nó có tác dụng.
"""

from __future__ import annotations

import copy
from typing import Any

from sqlalchemy.orm import Session

from src.models.db import SystemSetting

# Cấu hình mặc định. Mỗi khoá ở đây PHẢI có chỗ đọc trong report query.
DEFAULTS: dict[str, dict[str, Any]] = {
    "reports": {
        # Số ngày làm việc trước hạn thì hồ sơ vào diện "sắp trễ".
        "overdueWarningDays": 2,
        # Kỳ báo cáo mặc định khi giao diện không truyền date_from/date_to.
        "defaultPeriodDays": 30,
    },
}

# Khoảng hợp lệ cho từng khoá số. Kiểm ở đây thay vì trong Pydantic vì cùng một
# phép kiểm phải áp cho cả đường gọi trực tiếp từ script.
_RANGES: dict[tuple[str, str], tuple[int, int]] = {
    ("reports", "overdueWarningDays"): (1, 10),
    ("reports", "defaultPeriodDays"): (7, 365),
}


def get_settings(db: Session) -> dict[str, dict[str, Any]]:
    """Cấu hình hiện hành = mặc định trong code, ghi đè bởi phần đã lưu."""
    result = copy.deepcopy(DEFAULTS)
    for row in db.query(SystemSetting).all():
        if row.setting_key in result and isinstance(row.setting_value, dict):
            result[row.setting_key].update(row.setting_value)
    return result


def update_settings(
    db: Session, changes: dict[str, Any], user_id: int | None
) -> dict[str, dict[str, Any]]:
    """Ghi đè một phần cấu hình. Trả về toàn bộ cấu hình sau khi đổi.

    Khoá lạ bị TỪ CHỐI chứ không bỏ qua — xem docstring đầu file.
    """
    _validate(changes)

    for group, values in changes.items():
        row = db.get(SystemSetting, group)
        if row is None:
            # Chỉ lưu phần đã đổi, không chép cả nhóm mặc định vào.
            db.add(SystemSetting(setting_key=group, setting_value=dict(values), updated_by=user_id))
        else:
            # Gán dict MỚI thay vì sửa tại chỗ: SQLAlchemy không theo dõi được
            # thay đổi bên trong một JSON dict đã gắn vào session.
            row.setting_value = {**(row.setting_value or {}), **values}
            row.updated_by = user_id
    db.commit()
    return get_settings(db)


def _validate(changes: dict[str, Any]) -> None:
    for group, values in changes.items():
        if group not in DEFAULTS:
            raise ValueError(
                f"Nhóm cấu hình không hợp lệ: {group!r}. Chỉ có: {sorted(DEFAULTS)}"
            )
        if not isinstance(values, dict):
            raise ValueError(f"Nhóm {group!r} phải là object, nhận: {type(values).__name__}")

        for key, value in values.items():
            if key not in DEFAULTS[group]:
                raise ValueError(
                    f"Khoá không hợp lệ: {group}.{key}. Chỉ có: {sorted(DEFAULTS[group])}"
                )

            low, high = _RANGES[(group, key)]
            # `isinstance(True, int)` là True trong Python — không chặn thì
            # `True` lọt qua kiểm khoảng và lặng lẽ thành 1.
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{key} phải là số nguyên, nhận: {value!r}")
            if not low <= value <= high:
                raise ValueError(f"{key} phải nằm trong khoảng {low}–{high}, nhận: {value}")
