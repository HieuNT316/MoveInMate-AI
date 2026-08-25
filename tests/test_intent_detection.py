"""Nhận ý định làm thủ tục — cổng tất định, 3 lớp, và ranh giới với RAG.

Phần lớn giá trị của bộ test này nằm ở các ca **không** được vào luồng form:
mỗi ca như vậy là một câu hỏi thường mà nếu nhận nhầm thì US-05 (hỏi đáp kèm
nguồn) ngừng hoạt động với đúng câu đó.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.ai.intent import (
    _core_name,
    _normalize,
    detect_procedure_intent,
    wants_to_act,
)
from src.models.db import Base, ChecklistItem


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    """LLM giả — nhớ số lần bị gọi để kiểm cả ràng buộc chi phí."""

    def __init__(self, content: str = "khong_khop", error: Exception | None = None):
        self._content = content
        self._error = error
        self.calls = 0

    async def ainvoke(self, _prompt):
        self.calls += 1
        if self._error:
            raise self._error
        return _FakeResponse(self._content)


@pytest.fixture
def fake_llm(monkeypatch):
    """Gắn LLM giả, trả về nó để test xem đã bị gọi mấy lần."""

    llm = _FakeLLM()

    def _install(content: str = "khong_khop", error: Exception | None = None) -> _FakeLLM:
        llm._content = content
        llm._error = error
        return llm

    monkeypatch.setattr("src.ai.intent.get_chat_llm", lambda: llm)
    llm.install = _install  # type: ignore[attr-defined]
    return llm


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_factory()
    session.add(ChecklistItem(
        task_name="Đăng ký thẻ xe",
        item_type="bql_actionable",
        form_schema={"fields": [], "attachments": []},
    ))
    session.add(ChecklistItem(
        task_name="Đăng ký internet",
        item_type="bql_actionable",
        form_schema={"fields": [], "attachments": []},
    ))
    session.add(ChecklistItem(
        # Không có form — thủ tục chỉ cần xác nhận, không được mở luồng điền.
        task_name="Ký nội quy toà nhà",
        item_type="bql_actionable",
        form_schema=None,
    ))
    # Hai nhánh loại trừ nhau, tên chỉ khác phần trong ngoặc.
    for nhanh in ("chủ hộ", "người thuê"):
        session.add(ChecklistItem(
            task_name=f"Làm thẻ cư dân ({nhanh})",
            item_type="bql_actionable",
            form_schema={"fields": [], "attachments": []},
        ))
    # Tên có chữ "căn" — bẫy bỏ dấu trùng với "cần".
    session.add(ChecklistItem(
        task_name="Đăng ký chuyển đồ vào căn hộ",
        item_type="bql_actionable",
        form_schema={"fields": [], "attachments": []},
    ))
    session.commit()
    yield session
    session.close()
    engine.dispose()


# --- Hàm thuần -----------------------------------------------------------


def test_normalize():
    assert _normalize("Đăng ký") == "dang ky"
    assert _normalize("Ô tô") == "o to"


def test_core_name_bo_dong_tu_dau_va_phan_trong_ngoac():
    assert _core_name("Làm thẻ cư dân (chủ hộ)") == "the cu dan"
    assert _core_name("Đăng ký thẻ xe") == "the xe"


def test_wants_to_act_phan_biet_hoi_va_lam():
    assert wants_to_act("Cho tôi nộp hồ sơ thẻ xe")
    assert not wants_to_act("Làm thẻ xe cần giấy tờ gì?")


# --- Lớp 1 và 2 ----------------------------------------------------------


@pytest.mark.asyncio
async def test_khop_dung_mot_thu_tuc_thi_vao_luong_form(db_session, fake_llm):
    match = await detect_procedure_intent("Tôi muốn đăng ký thẻ xe máy", db_session)
    assert match.item is not None
    assert match.item.task_name == "Đăng ký thẻ xe"
    assert not match.ambiguous
    assert fake_llm.calls == 0, "khớp tất định rồi thì không được tốn lượt gọi LLM"


def test_loc_form_schema_phai_chay_trong_python(db_session):
    """Khoá lại cái bẫy đã làm hỏng ngày 24/08 (commit 8045c58, "M1").

    `JSONType` lưu `None` của Python thành chuỗi JSON `'null'`, không phải SQL
    NULL — nên lọc bằng `form_schema.isnot(None)` **không loại được gì**. Test
    này đỏ nghĩa là ai đó vừa chuyển bộ lọc xuống tầng SQL.
    """
    from sqlalchemy import text

    from src.ai.intent import _has_form

    raw = db_session.execute(
        text("SELECT form_schema FROM checklist_items WHERE task_name = 'Ký nội quy toà nhà'")
    ).scalar()
    assert raw == "null", "cột lưu chuỗi 'null', không phải SQL NULL"

    tat_ca = db_session.query(ChecklistItem).all()
    loc_bang_sql = db_session.query(ChecklistItem).filter(
        ChecklistItem.form_schema.isnot(None)
    ).all()
    assert len(loc_bang_sql) == len(tat_ca), "lọc ở SQL không loại được gì"

    loc_bang_python = [i for i in tat_ca if _has_form(i)]
    assert "Ký nội quy toà nhà" not in {i.task_name for i in loc_bang_python}
    assert len(loc_bang_python) == len(tat_ca) - 1


@pytest.mark.asyncio
async def test_thu_tuc_khong_co_form_thi_khong_mo_luong_form(db_session, fake_llm):
    """"Ký nội quy toà nhà" không có `form_schema` — phải để RAG trả lời."""
    match = await detect_procedure_intent("Tôi muốn làm thủ tục ký nội quy", db_session)
    assert match.item is None
    assert not match.ambiguous


@pytest.mark.asyncio
async def test_go_dung_ten_thu_tuc_thi_nhan_ra_du_co_ngoac(db_session, fake_llm):
    """"làm thẻ cư dân" phải khớp "Làm thẻ cư dân (chủ hộ)/(người thuê)".

    Trước 25/08 lớp 2 so nguyên chuỗi nên phần trong ngoặc làm trượt hoàn toàn:
    người dùng gõ đúng tên thủ tục mà hệ thống không nhận ra gì.
    """
    match = await detect_procedure_intent("làm thẻ cư dân", db_session)
    assert match.ambiguous, "hai nhánh chủ hộ/người thuê → phải hỏi lại"
    names = {i.task_name for i in match.disambiguation_options}
    assert names == {"Làm thẻ cư dân (chủ hộ)", "Làm thẻ cư dân (người thuê)"}


@pytest.mark.asyncio
async def test_bam_nut_chon_thu_tuc_thi_thoat_duoc_vong_hoi_lai(db_session, fake_llm):
    """Gửi KHÍT tên thủ tục phải ra đúng mục đó, không hỏi lại lần nữa.

    `web/app/chat/page.tsx` dựng mỗi lựa chọn thành nút, bấm nút thì gửi
    `task_name` làm `message`. Thiếu lớp khớp khít, câu đó rơi xuống lớp 2 (so
    phần lõi, đã bỏ ngoặc) nên lại khớp cả hai nhánh và AI hỏi lại đúng câu vừa
    hỏi — vòng lặp không lối ra. Test này đỏ nghĩa là vòng lặp quay lại.
    """
    hoi_lai = await detect_procedure_intent("thẻ cư dân", db_session)
    assert hoi_lai.ambiguous, "câu mơ hồ thì vẫn phải hỏi lại"

    for lua_chon in hoi_lai.disambiguation_options:
        da_chon = await detect_procedure_intent(lua_chon.task_name, db_session)
        assert not da_chon.ambiguous, f"bấm {lua_chon.task_name!r} mà vẫn bị hỏi lại"
        assert da_chon.item is not None
        assert da_chon.item.task_name == lua_chon.task_name


@pytest.mark.asyncio
async def test_cau_chung_chung_khong_bi_khop_bua_vao_mot_thu_tuc(db_session, fake_llm):
    """"tôi CẦN làm thủ tục" từng khớp `high` vào "…vào CĂN hộ".

    Bỏ dấu xong "cần" và "căn" đều thành "can". Câu hỏi chung chung phải nhường
    cho RAG, đừng kéo người ta vào một cái form họ không hỏi.
    """
    match = await detect_procedure_intent("tôi cần làm thủ tục", db_session)
    assert match.item is None
    assert not match.ambiguous


# --- Cổng tất định: câu hỏi thông tin không bao giờ vào form --------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    [
        # Ca nguy hiểm nhất: tên thủ tục nằm NGUYÊN trong câu nên lớp 2 khớp,
        # nhưng đuôi câu cho thấy người ta chỉ đang hỏi.
        "Đăng ký thẻ xe cần giấy tờ gì?",
        "Đăng ký thẻ xe mất bao lâu?",
        "Thủ tục đăng ký internet thế nào?",
    ],
)
async def test_cau_hoi_thong_tin_nhuong_cho_rag(db_session, fake_llm, question):
    match = await detect_procedure_intent(question, db_session)
    assert match.item is None
    assert not match.ambiguous, "câu hỏi thông tin mà hỏi lại thủ tục là chặn mất US-05"
    assert fake_llm.calls == 0, "câu hỏi thông tin không được tốn lượt gọi LLM"


@pytest.mark.asyncio
async def test_cau_ngoai_linh_vuc_nhuong_cho_rag(db_session, fake_llm):
    match = await detect_procedure_intent("Cho tôi xem thời tiết Hà Nội", db_session)
    assert match.item is None
    assert match.confidence == "low"
    assert not match.ambiguous
    assert fake_llm.calls == 0, "không có dấu hiệu hành động thì đừng gọi LLM"


# --- Lớp 3: LLM ----------------------------------------------------------


@pytest.mark.asyncio
async def test_lop_3_goi_llm_khi_hai_lop_dau_truot(db_session, fake_llm):
    """"xe bốn bánh" không trùng chữ nào với "Đăng ký thẻ xe" — chỉ LLM cứu được."""
    fake_llm.install("Đăng ký thẻ xe")
    match = await detect_procedure_intent(
        "Tôi muốn nộp hồ sơ cho con xe bốn bánh của mình", db_session
    )
    assert fake_llm.calls == 1
    assert match.item is not None
    assert match.item.task_name == "Đăng ký thẻ xe"
    assert not match.ambiguous


@pytest.mark.asyncio
async def test_llm_tra_khong_khop_thi_nhuong_cho_rag(db_session, fake_llm):
    fake_llm.install("khong_khop")
    match = await detect_procedure_intent("Cho tôi nộp cái gì đó không rõ", db_session)
    assert fake_llm.calls == 1
    assert match.item is None
    assert not match.ambiguous


@pytest.mark.asyncio
async def test_llm_bia_ten_thu_tuc_thi_bi_loai(db_session, fake_llm):
    """Tên không có trong danh sách = không khớp. LLM chỉ được CHỌN, không được ĐẶT TÊN."""
    fake_llm.install("Đăng ký thẻ máy bay")
    match = await detect_procedure_intent("Cho tôi nộp hồ sơ máy bay", db_session)
    assert match.item is None
    assert not match.ambiguous


@pytest.mark.asyncio
async def test_llm_them_loi_dan_thi_bi_loai(db_session, fake_llm):
    """Trả về đúng tên nhưng kèm lời dẫn cũng bị loại — so khớp phải khít."""
    fake_llm.install("Thủ tục phù hợp là: Đăng ký thẻ xe")
    match = await detect_procedure_intent("Cho tôi nộp hồ sơ xe", db_session)
    assert match.item is None


@pytest.mark.asyncio
async def test_llm_loi_thi_khong_lam_hong_chat(db_session, fake_llm):
    fake_llm.install(error=RuntimeError("timeout"))
    match = await detect_procedure_intent("Cho tôi nộp hồ sơ gì đó", db_session)
    assert match.item is None
    assert not match.ambiguous
