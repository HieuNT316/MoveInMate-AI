"""Bảng mã giấy tờ và phép suy "hồ sơ còn thiếu gì" (US-13 / D1).

Nhãn nằm ở ĐÂY, trong code, không nằm trong DB: sửa một chữ hiển thị không nên
phải viết migration. DB chỉ lưu mã.

Danh sách mã rút từ mục "Giấy tờ cần mang" trong `data/kb/bql/`. Đóng chứ không
phải chuỗi tự do — cùng lý do đã áp cho `AmenityPackage`: giá trị gõ lệch sẽ
không khớp gì cả và im lặng biến mất, không báo lỗi.
"""

from __future__ import annotations

from typing import Any

DOCUMENT_LABELS: dict[str, str] = {
    "cccd": "CCCD hoặc hộ chiếu",
    "bien_ban_ban_giao": "Biên bản bàn giao căn hộ",
    "hop_dong_thue": "Hợp đồng thuê nhà còn hiệu lực",
    "giay_uy_quyen": "Giấy uỷ quyền của chủ hộ",
    "dang_ky_xe": "Đăng ký xe (cà vẹt)",
    "the_cu_dan": "Thẻ cư dân đã được cấp",
    "the_xe": "Thẻ xe đã được cấp",
    "don_dang_ky": "Đơn đăng ký theo mẫu",
    "to_khai_ct01": "Tờ khai thay đổi thông tin cư trú (mẫu CT01)",
    "anh_vneid": "Ảnh màn hình VNeID hoặc giấy xác nhận cư trú",
    "khac": "Giấy tờ khác",
}

DOCUMENT_CODES = tuple(DOCUMENT_LABELS)


def describe(codes: list[str] | None) -> list[dict[str, str]]:
    """Kèm nhãn theo mã.

    Trả cả `label` chứ không riêng `code`: nếu chỉ trả mã thì frontend lại phải
    giữ một bảng nhãn của riêng nó — đúng chỗ nhân đôi mà D1 đang đi xoá.
    """
    return [
        {"code": c, "label": DOCUMENT_LABELS[c]} for c in (codes or []) if c in DOCUMENT_LABELS
    ]


def evaluate_documents(
    required: list[str] | None, attached: list[str | None]
) -> dict[str, Any]:
    """Đối chiếu giấy tờ thủ tục cần với những gì đã nộp.

    `attached` là loại của từng tệp; `None` nghĩa là tệp đã tải lên nhưng CHƯA
    được gán loại.

    Còn tệp chưa phân loại thì `missing_documents` trả **None** — nghĩa là
    "không kết luận được", chứ không phải "không thiếu gì". Đây là điểm cốt lõi:
    hồ sơ đang có ảnh cà vẹt mà báo "thiếu đăng ký xe" thì tệ hơn không báo gì,
    vì Ban quản lý nhìn vào tưởng cư dân chưa nộp và đi đòi thứ đã có.
    """
    unlabelled = sum(1 for a in attached if a is None)
    needed = [c for c in (required or []) if c in DOCUMENT_LABELS]

    if not needed:
        return {"missing_documents": [], "unlabelled_count": unlabelled}

    if unlabelled:
        return {"missing_documents": None, "unlabelled_count": unlabelled}

    have = {a for a in attached if a is not None}
    return {
        "missing_documents": describe([c for c in needed if c not in have]),
        "unlabelled_count": 0,
    }
