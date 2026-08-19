"""Che PII trước khi ghi `chat_history` (V8, `src/services/pii.py`).

Bài test này tồn tại để bảo vệ một quyết định thiết kế dễ làm sai: `question`
và `answer` bị che KHÁC NHAU (xem docstring module `pii.py`). Ba nhóm quan
trọng nhất, đúng thứ tự rủi ro nếu đổi sai:

  - Hotline BQL trong `answer` phải sống sót — đây là lý do `answer` không bị
    che số điện thoại. Che nhầm hotline nguy hiểm hơn cả không che gì, vì nó
    âm thầm xoá mất thông tin hữu ích nhất mà trợ lý đưa ra.
  - Số không phải định danh (phí, mã căn hộ, ngày tháng) phải xuyên qua
    nguyên vẹn — một bộ che ăn cả dữ liệu hợp lệ còn tệ hơn không che gì.
  - Cùng một số điện thoại: bị che ở `question`, sống ở `answer`.
"""

from src.services.pii import mask_answer, mask_question

CCCD_9 = "123456789"
CCCD_12 = "001234567890"
PHONE_10 = "0901234567"
PHONE_84_GROUPED = "+84 123 456 789"


# --- Hotline BQL trong answer phải sống sót ------------------------------


def test_hotline_bql_trong_answer_khong_bi_che():
    text = "Gọi an ninh: 0827 001 090 hoặc gửi xe: 0946 982 323"
    assert mask_answer(text) == text


def test_hotline_bql_trong_question_bi_che():
    """Ngược lại với answer: `question` che cả số điện thoại."""
    text = "Số của tôi là 0827 001 090"
    result = mask_question(text)
    assert "0827 001 090" not in result


# --- Số không phải định danh phải xuyên qua nguyên vẹn -------------------


def test_phi_7_chu_so_khong_bi_che():
    text = "Phí làm thẻ xe là 1.250.000đ"
    assert mask_question(text) == text
    assert mask_answer(text) == text


def test_ma_can_ho_khong_bi_che():
    text = "Căn hộ S2.03-1512 của tôi đã hoàn tất onboarding"
    assert mask_question(text) == text
    assert mask_answer(text) == text


def test_ngay_thang_khong_bi_che():
    text = "Tôi chuyển vào ngày 01/02/2024"
    assert mask_question(text) == text
    assert mask_answer(text) == text


# --- Số điện thoại: che ở question, sống ở answer ------------------------


def test_dien_thoai_10_so_bi_che_o_question():
    text = f"Gọi tôi số {PHONE_10} nhé"
    result = mask_question(text)
    assert PHONE_10 not in result
    assert "[ĐÃ ẨN THÔNG TIN CÁ NHÂN]" in result


def test_dien_thoai_10_so_khong_bi_che_o_answer():
    text = f"Hotline hỗ trợ: {PHONE_10}"
    assert mask_answer(text) == text


def test_dien_thoai_84_cach_nhom_3_so_khong_bi_che_o_answer():
    """Fix round 1: `+84 123 456 789` có 9 chữ số sau mã nước đứng ngay sau
    một dấu cách — trước fix, `(?<!\\d)` chỉ nhìn đúng 1 ký tự liền trước nên
    thoả mãn tại dấu cách đó, khiến `_CCCD_RE` nhận nhầm 9 chữ số này là CCCD
    và che mất số điện thoại ngay trong `answer`, nơi lẽ ra phải sống sót."""
    text = f"Hotline: {PHONE_84_GROUPED}"
    assert mask_answer(text) == text


def test_dien_thoai_84_cach_nhom_3_so_van_bi_che_o_question():
    """Fix không được mở lỗ hổng ngược: `question` vẫn phải che số này —
    `_PHONE_RE` (không phải `_CCCD_RE`) đã quét đúng toàn bộ số kèm mã nước,
    không phụ thuộc vào việc `_CCCD_RE` có bắt được hay không."""
    text = f"Số của tôi là {PHONE_84_GROUPED}"
    result = mask_question(text)
    assert PHONE_84_GROUPED not in result
    assert "123 456 789" not in result


# --- CCCD/CMND bị che ở cả hai trường -------------------------------------


def test_cccd_9_so_bi_che_o_ca_hai_truong():
    text = f"CCCD của tôi là {CCCD_9}"
    assert CCCD_9 not in mask_question(text)
    assert CCCD_9 not in mask_answer(text)


def test_cccd_12_so_bi_che_o_ca_hai_truong():
    text = f"CCCD của tôi là {CCCD_12}"
    assert CCCD_12 not in mask_question(text)
    assert CCCD_12 not in mask_answer(text)


def test_cccd_10_so_khong_khop_pattern_cccd():
    """Ranh giới quan trọng nhất của regex CCCD: số điện thoại 10 chữ số
    không phải 9 hay 12, nên không rơi vào CCCD — chỉ bị che ở `question`
    qua đường số điện thoại, không phải qua đường CCCD."""
    text = f"Số là {PHONE_10}"
    # Ở answer, không đường nào che số 10 chữ số này -> phải sống nguyên vẹn.
    assert mask_answer(text) == text


# --- Email bị che ở cả hai trường, kể cả khi chứa chữ số ------------------


def test_email_bi_che_o_ca_hai_truong():
    text = "Liên hệ: nguyenvana@gmail.com"
    assert "nguyenvana@gmail.com" not in mask_question(text)
    assert "nguyenvana@gmail.com" not in mask_answer(text)


def test_email_co_chu_so_trong_phan_local_khong_bi_cat_nham():
    """Email được che TRƯỚC CCCD/điện thoại: nếu đổi thứ tự, phần số trong
    local-part (vd `user.123456789@gmail.com`) sẽ bị CCCD/phone cắn mất một
    phần trước khi email kịp khớp trọn vẹn, để lại vệt che nham nhở dính domain
    thật. Che email trước xử lý trọn cụm trong một lần thế chỗ."""
    text = "Email tôi là user.123456789@gmail.com"
    result = mask_question(text)
    assert "gmail.com" not in result
    assert result.count("[ĐÃ ẨN THÔNG TIN CÁ NHÂN]") == 1
