"""AI dẫn dắt điền hồ sơ — hỏi từng trường, đọc câu trả lời, chốt bản tóm tắt."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.ai import form_dialog
from src.models.db import Base, ChecklistItem
from src.models.schemas import AttachmentSpecSchema, FormFieldSchema, FormSchemaPayload

VEHICLE_FORM = FormSchemaPayload(
    fields=[
        FormFieldSchema(
            key="vehicle_type", label="Loại phương tiện", type="select",
            options=["Ô tô", "Xe máy"], required=True,
            question="Bạn đăng ký thẻ xe gì?",
        ),
        FormFieldSchema(
            key="plate", label="Biển số xe", type="text", required=True,
            question="Biển số xe của bạn là gì?",
            pattern=r"^[0-9A-Z\-\.]{5,15}$",
        ),
        FormFieldSchema(
            key="quantity", label="Số lượng thẻ cần làm", type="number",
            required=False, default="1", question="Bạn cần làm bao nhiêu thẻ?",
        ),
    ],
    attachments=[
        AttachmentSpecSchema(code="cccd", label="Ảnh CCCD chủ phương tiện", required=True),
    ],
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    session.add(ChecklistItem(
        task_name="Đăng ký thẻ xe",
        item_type="bql_actionable",
        form_schema=VEHICLE_FORM.model_dump(),
    ))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def _field(key: str) -> FormFieldSchema:
    return next(f for f in VEHICLE_FORM.fields if f.key == key)


# --- Đọc câu trả lời vào một trường -------------------------------------


def test_select_khop_lua_chon():
    value, error = form_dialog.apply_answer(_field("vehicle_type"), "ô tô")
    assert (value, error) == ("Ô tô", None)


def test_select_khong_khop_thi_bao_lai_kem_lua_chon():
    value, error = form_dialog.apply_answer(_field("vehicle_type"), "xe đạp")
    assert value is None
    assert "Ô tô / Xe máy" in error


def test_so_viet_bang_chu_van_doc_duoc():
    assert form_dialog.apply_answer(_field("quantity"), "hai cái")[0] == "2"


def test_so_viet_bang_so():
    assert form_dialog.apply_answer(_field("quantity"), "3 thẻ")[0] == "3"


def test_truong_khong_bat_buoc_bo_qua_thi_dung_mac_dinh():
    assert form_dialog.apply_answer(_field("quantity"), "bỏ qua")[0] == "1"


def test_pattern_chap_nhan_cach_go_thuong_va_co_khoang_trang():
    """Cùng một biển số, gõ kiểu nào cũng phải nhận."""
    value, error = form_dialog.apply_answer(_field("plate"), "30a-123.45")
    assert error is None
    assert value == "30A-123.45"


def test_pattern_sai_thi_bao_loi_kem_gia_tri_da_go():
    value, error = form_dialog.apply_answer(_field("plate"), "xe của tôi màu đỏ")
    assert value is None
    assert "Biển số xe" in error


# --- Chọn trường để hỏi --------------------------------------------------


def test_hoi_theo_dung_thu_tu_khai_trong_schema():
    assert form_dialog.next_missing_field(VEHICLE_FORM, {}).key == "vehicle_type"
    assert form_dialog.next_missing_field(VEHICLE_FORM, {"vehicle_type": "Ô tô"}).key == "plate"
    assert form_dialog.next_missing_field(
        VEHICLE_FORM, {"vehicle_type": "Ô tô", "plate": "30A-12345", "quantity": "1"}
    ) is None


def test_cau_hoi_lay_nguyen_van_tu_field_question():
    question = form_dialog.build_question(_field("vehicle_type"))
    assert "Bạn đăng ký thẻ xe gì?" in question
    assert "Ô tô / Xe máy" in question


def test_truong_khong_bat_buoc_duoc_noi_ro_la_co_the_bo_qua():
    question = form_dialog.build_question(_field("quantity"))
    assert "bỏ qua" in question
    assert "mặc định 1" in question


# --- Nhặt sẵn từ câu mở đầu ---------------------------------------------


def test_nhat_san_lua_chon_va_bien_so_ngay_trong_cau_dau():
    seeded = form_dialog.seed_from_message(
        VEHICLE_FORM, "Tôi muốn đăng ký thẻ xe máy biển 29P1-123.45"
    )
    assert seeded["vehicle_type"] == "Xe máy"
    assert seeded["plate"] == "29P1-123.45"


def test_khong_doan_bua_truong_chu_tu_do():
    """Câu không có biển số thì để trống và hỏi, đừng gán cả câu vào ô biển số."""
    seeded = form_dialog.seed_from_message(VEHICLE_FORM, "Tôi muốn đăng ký thẻ xe")
    assert "plate" not in seeded


# --- Trọn một luồng ------------------------------------------------------


@pytest.mark.asyncio
async def test_tron_luong_hoi_tung_truong_roi_chot_ho_so(db_session, monkeypatch):
    # LLM hỏng có chủ ý: các câu dưới đây phải khớp bằng lớp tất định (keyword
    # / fuzzy). Test đỏ ở đây nghĩa là luồng đã âm thầm phụ thuộc vào LLM.
    monkeypatch.setattr("src.ai.intent.get_chat_llm", lambda: None)

    # Lượt 1 — nhận ý định, chưa khai gì nên hỏi trường đầu tiên.
    turn = await form_dialog.run_form_turn(
        db_session, "Tôi muốn đăng ký thẻ xe", None, None
    )
    assert turn.intent == "form_generation"
    assert "Bạn đăng ký thẻ xe gì?" in turn.answer
    item_id = turn.checklist_item_id

    # Lượt 2 — trả lời trường đầu, được hỏi trường thứ hai.
    turn = await form_dialog.run_form_turn(db_session, "ô tô", item_id, turn.form_data)
    assert turn.form_data["vehicle_type"] == "Ô tô"
    assert "Biển số xe của bạn là gì?" in turn.answer

    # Lượt 3 — trả lời sai định dạng, phải hỏi LẠI đúng trường đó.
    turn = await form_dialog.run_form_turn(db_session, "không nhớ", item_id, turn.form_data)
    assert "plate" not in turn.form_data
    assert "Biển số xe của bạn là gì?" in turn.answer

    # Lượt 4 — trả lời đúng, sang trường cuối.
    turn = await form_dialog.run_form_turn(db_session, "30A-123.45", item_id, turn.form_data)
    assert turn.form_data["plate"] == "30A-123.45"
    assert "bao nhiêu thẻ" in turn.answer

    # Lượt 5 — đủ trường, chốt bản tóm tắt để cư dân xem lại.
    turn = await form_dialog.run_form_turn(db_session, "2", item_id, turn.form_data)
    assert turn.intent == "form_review"
    assert turn.form_data == {"vehicle_type": "Ô tô", "plate": "30A-123.45", "quantity": "2"}
    assert "Ảnh CCCD chủ phương tiện" in turn.answer, "phải nhắc giấy tờ cần đính kèm"


@pytest.mark.asyncio
async def test_khai_du_ngay_cau_dau_thi_chot_luon(db_session, monkeypatch):
    # LLM hỏng có chủ ý: các câu dưới đây phải khớp bằng lớp tất định (keyword
    # / fuzzy). Test đỏ ở đây nghĩa là luồng đã âm thầm phụ thuộc vào LLM.
    monkeypatch.setattr("src.ai.intent.get_chat_llm", lambda: None)
    turn = await form_dialog.run_form_turn(
        db_session, "Tôi muốn đăng ký thẻ xe máy biển 29P1-123.45", None, None
    )
    # Còn `quantity` chưa khai nên vẫn hỏi thêm một lượt, nhưng hai trường bắt
    # buộc đã nhặt được ngay từ câu đầu.
    assert turn.form_data["vehicle_type"] == "Xe máy"
    assert turn.form_data["plate"] == "29P1-123.45"


@pytest.mark.asyncio
async def test_cau_hoi_thong_tin_khong_giu_luot(db_session, monkeypatch):
    """Trả None = nhường cho RAG. Đây là hợp đồng giữ US-05 sống."""
    # LLM hỏng có chủ ý: các câu dưới đây phải khớp bằng lớp tất định (keyword
    # / fuzzy). Test đỏ ở đây nghĩa là luồng đã âm thầm phụ thuộc vào LLM.
    monkeypatch.setattr("src.ai.intent.get_chat_llm", lambda: None)
    turn = await form_dialog.run_form_turn(
        db_session, "Đăng ký thẻ xe cần giấy tờ gì?", None, None
    )
    assert turn is None
