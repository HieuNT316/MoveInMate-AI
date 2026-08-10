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
from src.services.vectorstore import RetrievalError


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeLLM:
    def __init__(self, content: str = "Câu trả lời giả lập.", error: Exception | None = None):
        self._content = content
        self._error = error

    async def ainvoke(self, _messages):
        if self._error:
            raise self._error
        return _FakeResponse(self._content)


class _FakeStore:
    def __init__(self, results: list[tuple[LCDocument, float]]):
        self._results = results

    def similarity_search_with_score(self, _query: str, k: int):
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


async def _run(monkeypatch, store: _FakeStore, llm: _FakeLLM, query: str = "Làm thẻ xe cần gì?"):
    monkeypatch.setattr(rag_retrieve_module, "get_vectorstore", lambda: store)
    monkeypatch.setattr(generate_module, "get_chat_llm", lambda: llm)
    chat_graph = graph_module.build_chat_graph()
    return await chat_graph.ainvoke({"query": query})


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
