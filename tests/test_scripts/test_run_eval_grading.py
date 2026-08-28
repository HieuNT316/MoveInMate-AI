"""`scripts/run_eval.py::_grade` — chấm điểm thuần, không gọi mạng.

Tập trung vào nhánh `form_generation`/`disambiguation` thêm 28/08: trước đó
`_grade` áp luật của RAG (answer_source/sources) lên hai câu này và LUÔN chấm
sai bất kể luồng điền hồ sơ có chạy đúng hay không — hỏng thầm lặng vì script
vẫn chạy, vẫn in FAIL, chỉ là vì lý do sai.
"""

from scripts.run_eval import _grade, _percentile


def _question(**overrides) -> dict:
    base = {"id": "Q1", "procedure": "Đăng ký thẻ xe", "expect": "answer"}
    return {**base, **overrides}


# --- Câu hỏi thường (answer / refuse) — hành vi cũ phải giữ nguyên ---------


def test_cau_tra_loi_duoc_dung_thi_pass():
    row = _grade(
        _question(must_mention=["CCCD"]),
        {"answer": "Cần CCCD bản gốc.", "answer_source": "rag",
         "sources": [{"title": "Quy chế"}]},
    )
    assert row["passed"]


def test_cau_tra_loi_thieu_tu_khoa_thi_fail():
    row = _grade(
        _question(must_mention=["CCCD"]),
        {"answer": "Mang giấy tờ tuỳ thân.", "answer_source": "rag",
         "sources": [{"title": "Quy chế"}]},
    )
    assert not row["passed"]
    assert "CCCD" in row["missing_terms"]


def test_cau_tu_choi_ma_van_kem_nguon_thi_fail():
    """Đúng bug V3/B5 — trích dẫn dưới câu "tôi không biết" không được lọt."""
    row = _grade(
        _question(expect="refuse"),
        {"answer": "Xin lỗi, tôi chưa tìm thấy.", "answer_source": "no_context",
         "sources": [{"title": "Tài liệu không liên quan"}]},
    )
    assert not row["passed"]
    assert not row["cited_ok"]


# --- FG01/FG02: intent, không phải answer_source ---------------------------


def test_form_generation_dung_intent_va_dung_field_thi_pass():
    row = _grade(
        _question(
            id="FG01", expect="form_generation",
            expected_fields={"vehicle_type": "Xe máy", "plate": "29P1-123.45"},
        ),
        {
            "answer": "Bạn đăng ký thẻ xe gì?",
            "answer_source": "no_context",  # bình thường cho luồng form, KHÔNG phải từ chối
            "intent": "form_generation",
            "form_data": {"vehicle_type": "Xe máy", "plate": "29P1-123.45"},
            "sources": [],
        },
    )
    assert row["passed"], row


def test_form_generation_sai_intent_thi_fail():
    """Trước bản sửa: answer_source="no_context" luôn bị coi là "đúng loại"
    SAI cho câu form_generation, bất kể `intent` thật sự là gì."""
    row = _grade(
        _question(id="FG01", expect="form_generation", expected_fields={}),
        {"answer": "...", "answer_source": "no_context", "intent": "qa", "sources": []},
    )
    assert not row["passed"]
    assert not row["right_kind"]


def test_form_generation_field_sai_thi_fail_va_bao_ro_field_nao():
    row = _grade(
        _question(
            id="FG01", expect="form_generation",
            expected_fields={"vehicle_type": "Xe máy"},
        ),
        {
            "answer": "...", "answer_source": "no_context", "intent": "form_generation",
            "form_data": {"vehicle_type": "Ô tô"}, "sources": [],
        },
    )
    assert not row["passed"]
    assert any("vehicle_type" in m for m in row["missing_terms"])


def test_form_generation_khong_bi_doi_hoi_phai_co_sources():
    """Luồng form không truy xuất tài liệu — đòi `sources` là chấm sai chỗ."""
    row = _grade(
        _question(id="FG01", expect="form_generation", expected_fields={}),
        {"answer": "...", "answer_source": "no_context", "intent": "form_generation", "sources": []},
    )
    assert row["cited_ok"]


def test_disambiguation_dung_intent_thi_pass():
    row = _grade(
        _question(id="FG02", expect="disambiguation"),
        {"answer": "Bạn muốn chủ hộ hay người thuê?", "answer_source": "no_context",
         "intent": "disambiguation", "sources": []},
    )
    assert row["passed"]


# --- _percentile -----------------------------------------------------------


def test_percentile_danh_sach_rong_tra_none():
    assert _percentile([], 0.5) is None


def test_percentile_mot_phan_tu():
    assert _percentile([42.0], 0.95) == 42.0


def test_percentile_p50_p95():
    data = sorted([100.0, 200.0, 300.0, 400.0, 500.0])
    assert _percentile(data, 0.50) == 300.0
    assert _percentile(data, 0.95) == 480.0
