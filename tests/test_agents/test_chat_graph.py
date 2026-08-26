"""Test `chat_graph` — mock vectorstore + LLM (docs/architecture_diagram.md mục 6).

Kiểm tra logic điều hướng, KHÔNG kiểm tra chất lượng văn bản LLM: trúng
ngưỡng có bỏ qua LLM không, không có context có từ chối không, sources có gộp
trùng không, lỗi hạ tầng có lan đúng loại exception không.
"""

from __future__ import annotations

import pytest
from langchain_core.documents import Document as LCDocument

from src.agents import graph as graph_module
from src.agents.nodes import generate as generate_module
from src.agents.nodes import rag_retrieve as rag_retrieve_module
from src.agents.nodes import rewrite_query as rewrite_query_module
from src.services.vectorstore import RetrievalError


class _FakeResponse:
    def __init__(self, content: str = "", tool_calls: list[dict] | None = None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeLLM:
    """`responses` mô phỏng dãy lượt gọi (vd. lượt 1 tool_call, lượt 2 văn bản
    cuối). Không truyền `responses` thì mọi lượt gọi đều trả về `content`."""

    def __init__(
        self,
        content: str = "Câu trả lời giả lập.",
        error: Exception | None = None,
        responses: list[_FakeResponse] | None = None,
    ):
        self._content = content
        self._error = error
        self._responses = responses
        self._call_index = 0

    def bind_tools(self, _tools):
        return self

    async def ainvoke(self, _messages):
        if self._error:
            raise self._error
        if self._responses is not None:
            response = self._responses[min(self._call_index, len(self._responses) - 1)]
            self._call_index += 1
            return response
        return _FakeResponse(self._content)


class _FakeStore:
    def __init__(self, results: list[tuple[LCDocument, float]]):
        self._results = results
        # Ghi lại câu truy vấn thật sự gửi tới Chroma — dùng để xác nhận
        # rag_retrieve có ưu tiên `standalone_query` đã viết lại hay không.
        self.received_queries: list[str] = []

    def similarity_search_with_score(self, query: str, k: int):
        self.received_queries.append(query)
        return self._results[:k]


def _doc(content: str, document_id: int, title: str, source_type: str = "bql_internal"):
    return LCDocument(
        page_content=content,
        metadata={"document_id": document_id, "title": title, "source_type": source_type},
    )


@pytest.fixture(autouse=True)
def _fresh_graph():
    """Xây lại graph mỗi test — tránh rò rỉ patch giữa các test."""
    yield


async def _run(
    monkeypatch,
    store: _FakeStore,
    llm: _FakeLLM,
    query: str = "Làm thẻ xe cần gì?",
    chat_history: list[dict[str, str]] | None = None,
    rewrite_llm: _FakeLLM | None = None,
):
    monkeypatch.setattr(rag_retrieve_module, "get_vectorstore", lambda: store)
    monkeypatch.setattr(generate_module, "get_chat_llm", lambda: llm)
    # Không có lịch sử thì rewrite_query bỏ qua, không gọi LLM — mặc định
    # dùng chung fake với generate cho gọn, chỉ tách riêng khi test cần.
    monkeypatch.setattr(rewrite_query_module, "get_chat_llm", lambda: rewrite_llm or llm)
    chat_graph = graph_module.build_chat_graph()
    return await chat_graph.ainvoke({"query": query, "chat_history": chat_history or []})


@pytest.mark.asyncio
async def test_co_context_thi_tra_loi_va_kem_nguon(monkeypatch):
    store = _FakeStore([(_doc("Nội dung A", 1, "Tài liệu A"), 0.1)])
    result = await _run(monkeypatch, store, _FakeLLM("Đây là câu trả lời."))

    assert result["answer_source"] == "rag"
    assert result["answer"] == "Đây là câu trả lời."
    assert result["sources"] == [
        {"document_id": 1, "title": "Tài liệu A", "snippet": "Nội dung A", "source_type": "bql_internal"}
    ]


@pytest.mark.asyncio
async def test_khong_co_chunk_nao_thi_tu_choi_khong_goi_llm(monkeypatch):
    store = _FakeStore([])
    llm = _FakeLLM(error=AssertionError("generate không được gọi LLM khi không có context"))
    result = await _run(monkeypatch, store, llm)

    assert result["answer_source"] == "no_context"
    assert result["sources"] == []
    assert "Ban quản lý" in result["answer"]


@pytest.mark.asyncio
async def test_chunk_vuot_nguong_bi_loai_va_tu_choi(monkeypatch):
    """Điểm càng cao = càng xa — vượt `rag_max_distance` phải bị loại như rỗng."""
    from src.config import get_settings

    far_away = get_settings().rag_max_distance + 0.5
    store = _FakeStore([(_doc("Nội dung không liên quan", 9, "Tài liệu lạc đề"), far_away)])
    llm = _FakeLLM(error=AssertionError("không được gọi LLM khi mọi chunk vượt ngưỡng"))
    result = await _run(monkeypatch, store, llm)

    assert result["answer_source"] == "no_context"
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_nhieu_chunk_cung_tai_lieu_chi_gop_thanh_mot_nguon(monkeypatch):
    store = _FakeStore(
        [
            (_doc("Đoạn 1", 5, "Quy trình X"), 0.05),
            (_doc("Đoạn 2", 5, "Quy trình X"), 0.08),
            (_doc("Đoạn khác", 6, "Quy trình Y"), 0.1),
        ]
    )
    result = await _run(monkeypatch, store, _FakeLLM("ok"))

    document_ids = [s["document_id"] for s in result["sources"]]
    assert document_ids == [5, 6]


@pytest.mark.asyncio
async def test_loi_ha_tang_embedding_lan_thanh_retrieval_error(monkeypatch):
    class _BrokenStore:
        def similarity_search_with_score(self, _query, k):
            raise ConnectionError("Google API sập")

    with pytest.raises(RetrievalError):
        await _run(monkeypatch, _BrokenStore(), _FakeLLM())


@pytest.mark.asyncio
async def test_llm_loi_van_tra_ve_sources_da_truy_xuat(monkeypatch):
    """Lỗi một phần: context đã có, chỉ generate hỏng — không được mất sources (mục 5)."""
    store = _FakeStore([(_doc("Nội dung A", 1, "Tài liệu A"), 0.1)])
    result = await _run(monkeypatch, store, _FakeLLM(error=TimeoutError("hết giờ")))

    assert result["answer_source"] == "rag"
    assert result["sources"]
    assert result["sources"][0]["document_id"] == 1


# --- Tool điều hướng nộp hồ sơ -------------------------------------------


def _tool_call_response(procedure_name: str) -> _FakeResponse:
    return _FakeResponse(
        tool_calls=[
            {
                "name": "request_submission_navigation",
                "args": {"procedure_name": procedure_name},
                "id": "call_1",
            }
        ]
    )


@pytest.mark.asyncio
async def test_goi_tool_dieu_huong_thi_tra_ve_suggested_action(monkeypatch):
    store = _FakeStore([(_doc("Nội dung A", 1, "Đăng ký thẻ xe"), 0.1)])
    llm = _FakeLLM(
        responses=[
            _tool_call_response("Đăng ký thẻ xe"),
            _FakeResponse(content="Bạn có muốn tôi đưa bạn tới đó không?"),
        ]
    )
    result = await _run(monkeypatch, store, llm, query="Nộp hồ sơ thẻ xe ở đâu?")

    assert result["answer"] == "Bạn có muốn tôi đưa bạn tới đó không?"
    assert result["suggested_action"] == {
        "type": "navigate_to_submission",
        "procedure_name": "Đăng ký thẻ xe",
    }


@pytest.mark.asyncio
async def test_khong_goi_tool_thi_khong_co_suggested_action(monkeypatch):
    store = _FakeStore([(_doc("Nội dung A", 1, "Tài liệu A"), 0.1)])
    result = await _run(monkeypatch, store, _FakeLLM("Câu trả lời thường."))

    assert "suggested_action" not in result


@pytest.mark.asyncio
async def test_loi_o_luot_hai_van_giu_duoc_suggested_action(monkeypatch):
    """LLM lỗi ở lượt xác nhận cuối — vẫn phải giữ được tín hiệu điều hướng đã có."""

    class _FailSecondCallLLM(_FakeLLM):
        async def ainvoke(self, messages):
            if self._call_index == 0:
                self._call_index += 1
                return _tool_call_response("Đăng ký thẻ cư dân")
            raise TimeoutError("hết giờ ở lượt hai")

    store = _FakeStore([(_doc("Nội dung A", 1, "Đăng ký thẻ cư dân"), 0.1)])
    result = await _run(monkeypatch, store, _FailSecondCallLLM())

    assert result["answer_source"] == "rag"
    assert result["suggested_action"]["procedure_name"] == "Đăng ký thẻ cư dân"


# --- Viết lại câu hỏi có ngữ cảnh (multi-turn) ----------------------------


@pytest.mark.asyncio
async def test_khong_co_lich_su_thi_khong_viet_lai_cau_hoi(monkeypatch):
    """Câu hỏi đầu tiên của hội thoại luôn tự đủ nghĩa — không tốn thêm lệnh gọi LLM."""
    store = _FakeStore([(_doc("Nội dung A", 1, "Tài liệu A"), 0.1)])
    rewrite_llm = _FakeLLM(error=AssertionError("không có lịch sử thì không được gọi LLM viết lại"))
    await _run(monkeypatch, store, _FakeLLM("ok"), rewrite_llm=rewrite_llm)

    assert store.received_queries == ["Làm thẻ xe cần gì?"]


@pytest.mark.asyncio
async def test_co_lich_su_thi_viet_lai_va_dung_cau_da_viet_lai_de_truy_xuat(monkeypatch):
    """Câu hỏi mơ hồ ('còn phí thì sao') được viết lại độc lập ngữ cảnh trước khi truy xuất."""
    store = _FakeStore([(_doc("Phí thẻ xe 50k/tháng", 1, "Bảng phí"), 0.1)])
    rewrite_llm = _FakeLLM("Thẻ xe có mất phí không?")
    history = [{"question": "Thẻ xe cần giấy tờ gì?", "answer": "Cần CCCD và cà vẹt xe."}]

    result = await _run(
        monkeypatch,
        store,
        _FakeLLM("Có, thẻ xe mất phí."),
        query="Còn phí thì sao?",
        chat_history=history,
        rewrite_llm=rewrite_llm,
    )

    # rag_retrieve phải nhận câu ĐÃ VIẾT LẠI, không phải câu gốc mơ hồ.
    assert store.received_queries == ["Thẻ xe có mất phí không?"]
    assert result["answer_source"] == "rag"


@pytest.mark.asyncio
async def test_loi_viet_lai_cau_hoi_khong_chan_ca_pipeline(monkeypatch):
    """Lỗi ở bước viết lại (phụ trợ) không được làm hỏng cả request — rơi về câu gốc."""
    store = _FakeStore([(_doc("Nội dung A", 1, "Tài liệu A"), 0.1)])
    rewrite_llm = _FakeLLM(error=TimeoutError("hết giờ lúc viết lại"))
    history = [{"question": "Câu trước", "answer": "Trả lời trước"}]

    result = await _run(
        monkeypatch,
        store,
        _FakeLLM("Vẫn trả lời được."),
        query="Câu hỏi mơ hồ",
        chat_history=history,
        rewrite_llm=rewrite_llm,
    )

    assert store.received_queries == ["Câu hỏi mơ hồ"]  # rơi về câu gốc
    assert result["answer"] == "Vẫn trả lời được."


# --- Guard tầng 2: có tài liệu nhưng tài liệu không chứa câu trả lời -------
#
# Chế độ hỏng nguy hiểm nhất còn lại theo charter mục 11, đo được 0/3 ở
# eval/results/report.md mục 2. Hai chiều đều phải đúng: bắt được câu từ chối
# thật, và KHÔNG bắt nhầm câu trả lời được một phần.


@pytest.mark.asyncio
async def test_llm_bao_khong_co_trong_tai_lieu_thi_bo_luon_trich_dan(monkeypatch):
    """Mã quy ước → từ chối chuẩn, `no_context`, và sources rỗng.

    Bỏ sources là nửa quan trọng: hiện khối "Nguồn trích dẫn" ngay dưới câu
    "tôi không biết" làm câu trả lời trông đáng tin đúng lúc nó rỗng nội dung.
    """
    store = _FakeStore([(_doc("Phí dịch vụ 2026...", 1, "Phí dịch vụ VSC"), 0.30)])
    result = await _run(
        monkeypatch, store,
        _FakeLLM(generate_module.NO_ANSWER_SENTINEL),
        query="Phí bảo trì 2% của căn hộ tôi là bao nhiêu?",
    )

    assert result["answer_source"] == "no_context"
    assert result["sources"] == [], "không trả lời được thì không được trích dẫn gì"
    assert result["answer"] == generate_module.REFUSAL_WITH_TICKET
    assert generate_module.NO_ANSWER_SENTINEL not in result["answer"], "mã nội bộ không được lộ ra"


@pytest.mark.asyncio
async def test_llm_khong_dung_ma_quy_uoc_van_bi_bat(monkeypatch):
    """Lưới dự phòng — LLM viết câu từ chối bằng lời lẽ tự do."""
    store = _FakeStore([(_doc("Nội dung", 1, "Quy chế"), 0.30)])
    result = await _run(
        monkeypatch, store,
        _FakeLLM("Tôi không tìm thấy thông tin này trong tài liệu được cung cấp."),
    )

    assert result["answer_source"] == "no_context"
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_tra_loi_duoc_mot_phan_thi_khong_bi_coi_la_tu_choi(monkeypatch):
    """Câu dài có chữ "không đề cập" vẫn là câu trả lời — phải giữ nguyên nguồn.

    Chặn nhầm ở đây tệ hơn để lọt: người dùng mất phần thông tin thật sự có.
    """
    store = _FakeStore([(_doc("Nội dung", 1, "Quy chế"), 0.20)])
    cau_tra_loi = (
        "Tài liệu không đề cập mức phí cụ thể cho căn 2 phòng ngủ, nhưng có nêu "
        "cách tính: phí dịch vụ được thu theo diện tích sử dụng căn hộ, đơn giá "
        "công bố hằng năm và thông báo tới cư dân trước ít nhất 30 ngày. Bạn có "
        "thể đối chiếu diện tích trên hợp đồng mua bán để ước tính."
    )
    result = await _run(monkeypatch, store, _FakeLLM(cau_tra_loi))

    assert result["answer_source"] == "rag"
    assert result["answer"] == cau_tra_loi
    assert result["sources"], "trả lời được thì phải kèm nguồn"


@pytest.mark.asyncio
async def test_cau_tra_loi_binh_thuong_chua_chu_khong_van_giu_nguyen(monkeypatch):
    """"Hồ sơ không cần công chứng" là thông tin, không phải lời từ chối."""
    store = _FakeStore([(_doc("Nội dung", 1, "Quy chế"), 0.20)])
    result = await _run(
        monkeypatch, store, _FakeLLM("Hồ sơ không cần công chứng, chỉ cần bản sao CCCD.")
    )

    assert result["answer_source"] == "rag"
    assert result["sources"]


# --- US-11: mời mở ticket, nhưng chỉ đúng chỗ ----------------------------


@pytest.mark.asyncio
async def test_dung_linh_vuc_ma_kb_thieu_thi_moi_gui_cho_bql(monkeypatch):
    """Đây là loại câu BQL trả lời được và NÊN biết là cư dân đang hỏi.

    Mỗi ticket ở đây là một chỗ trống trong KB tự báo cáo về.
    """
    store = _FakeStore([(_doc("Phí dịch vụ 2026...", 1, "Phí dịch vụ VSC"), 0.30)])
    result = await _run(
        monkeypatch, store,
        _FakeLLM(generate_module.NO_ANSWER_SENTINEL),
        query="Phí bảo trì 2% của căn hộ tôi là bao nhiêu?",
    )

    assert result["ticket_suggested"] is True
    assert result["answer_source"] == "no_context"
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_cau_ngoai_linh_vuc_thi_tu_choi_nhung_khong_moi_mo_ticket(monkeypatch):
    """"Cho tôi công thức nấu phở bò" — từ chối, nhưng đừng mời gửi cho BQL.

    Không đoạn nào qua được ngưỡng khoảng cách nghĩa là câu nằm ngoài lĩnh
    vực. Mời mở ticket ở đây vừa vô duyên vừa làm ngập hộp thư BQL bằng những
    câu họ không có trách nhiệm trả lời.
    """
    result = await _run(
        monkeypatch, _FakeStore([]), _FakeLLM(),
        query="Cho tôi công thức nấu phở bò.",
    )

    assert result["answer_source"] == "no_context"
    assert result["ticket_suggested"] is False
    assert result["answer"] == generate_module.REFUSAL, "câu từ chối gọn, không mời gì"


@pytest.mark.asyncio
async def test_tra_loi_duoc_thi_khong_moi_mo_ticket(monkeypatch):
    store = _FakeStore([(_doc("Nội dung A", 1, "Tài liệu A"), 0.1)])
    result = await _run(monkeypatch, store, _FakeLLM("Đây là câu trả lời."))
    assert result.get("ticket_suggested", False) is False
