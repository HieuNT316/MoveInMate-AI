"""Bảng mã giấy tờ và phép suy "còn thiếu gì" (US-13 / D1).

Hai nhóm test ở đây là hai sửa đổi bắt buộc rút ra khi rà soát thiết kế:

  - Không được khẳng định "thiếu giấy tờ X" khi hồ sơ còn tệp CHƯA PHÂN LOẠI.
    Trả `None` (không kết luận) thay vì một danh sách nghe chắc chắn mà sai.
  - Bảng chép tay từ KB phải có thứ canh. Định tuyến đã dính đúng lỗi này:
    checklist ghi "hồ bơi", KB ghi "bể bơi", lệch âm thầm cho tới khi tình cờ
    phát hiện.
"""

from pathlib import Path

import pytest

from scripts.seed_data import CHECKLIST_ITEMS
from src.services.documents import DOCUMENT_LABELS, describe, evaluate_documents

ROUTING_TABLE = Path("data/kb/bql/bql-co-cau-va-quy-trinh.md")


# --- Suy ra còn thiếu gì -------------------------------------------------


def test_du_giay_to_thi_khong_thieu_gi():
    result = evaluate_documents(["cccd", "dang_ky_xe"], ["cccd", "dang_ky_xe"])
    assert result["missing_documents"] == []
    assert result["unlabelled_count"] == 0


def test_thieu_mot_loai_thi_bao_dung_loai_do():
    result = evaluate_documents(["cccd", "dang_ky_xe"], ["cccd"])
    assert [d["code"] for d in result["missing_documents"]] == ["dang_ky_xe"]


def test_con_tep_chua_phan_loai_thi_khong_ket_luan():
    """Điểm quan trọng nhất của D1.

    Hồ sơ có ảnh cà vẹt nhưng chưa gán loại mà báo "thiếu đăng ký xe" thì tệ
    hơn không báo gì: Ban quản lý nhìn vào tưởng cư dân chưa nộp.
    """
    result = evaluate_documents(["cccd", "dang_ky_xe"], [None, None])
    assert result["missing_documents"] is None
    assert result["unlabelled_count"] == 2


def test_vua_co_phan_loai_vua_con_bo_sot_thi_van_khong_ket_luan():
    result = evaluate_documents(["cccd", "dang_ky_xe"], ["cccd", None])
    assert result["missing_documents"] is None
    assert result["unlabelled_count"] == 1


def test_thu_tuc_khong_can_giay_to_thi_khong_bao_gio_thieu():
    result = evaluate_documents([], [None])
    assert result["missing_documents"] == []


def test_khac_la_lua_chon_co_chu_y_khong_phai_chua_phan_loai():
    """`khac` nghĩa là cư dân đã gán, chỉ là không thuộc loại nào — khác hẳn
    NULL. Gộp hai thứ này lại là mất khả năng phân biệt."""
    result = evaluate_documents(["cccd"], ["khac"])
    assert result["unlabelled_count"] == 0
    assert [d["code"] for d in result["missing_documents"]] == ["cccd"]


def test_nop_thua_loai_khong_lam_hong_phep_tinh():
    result = evaluate_documents(["cccd"], ["cccd", "hop_dong_thue"])
    assert result["missing_documents"] == []


def test_describe_tra_kem_nhan_de_frontend_khoi_giu_bang_rieng():
    assert describe(["cccd"]) == [{"code": "cccd", "label": DOCUMENT_LABELS["cccd"]}]


# --- Canh bảng chép tay từ KB -------------------------------------------


@pytest.mark.parametrize(
    "item", [i for i in CHECKLIST_ITEMS if i.get("required_documents")]
)
def test_moi_ma_giay_to_deu_co_nhan(item):
    unknown = sorted(set(item["required_documents"]) - set(DOCUMENT_LABELS))
    assert not unknown, f"{item['task_name']!r} dùng mã lạ: {unknown}"


@pytest.mark.parametrize(
    "item", [i for i in CHECKLIST_ITEMS if i["item_type"] == "bql_actionable"]
)
def test_ten_thu_tuc_khop_bang_dinh_tuyen_trong_kb(item):
    """Phép thử lẽ ra đã bắt được vụ "hồ bơi" / "bể bơi"."""
    assert item["task_name"] in ROUTING_TABLE.read_text(encoding="utf-8"), (
        f"{item['task_name']!r} không có trong bảng định tuyến của KB — "
        "tên lệch thì không tra được bộ phận lẫn giấy tờ"
    )
