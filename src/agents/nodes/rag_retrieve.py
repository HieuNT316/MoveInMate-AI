"""Node `rag_retrieve` — docs/architecture_diagram.md mục 3.4."""

from typing import Any

from starlette.concurrency import run_in_threadpool

from src.agents.state import ChatState
from src.config import get_settings
from src.services.vectorstore import RetrievalError, get_vectorstore

_SNIPPET_LEN = 220


def _snippet(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _SNIPPET_LEN else text[: _SNIPPET_LEN - 1].rstrip() + "…"


async def rag_retrieve_node(state: ChatState) -> dict[str, Any]:
    """Embed câu hỏi, tìm top-k chunk liên quan, gộp `sources[]` theo document_id.

    `sources[]` là output tất định của bước này, không phải LLM tự liệt kê
    (bảo đảm #1 của thiết kế) — gộp trùng ở đây để một tài liệu không xuất
    hiện nhiều lần chỉ vì nhiều chunk của nó cùng khớp.
    """
    settings = get_settings()
    store = get_vectorstore()
    # Ưu tiên câu đã viết lại độc lập ngữ cảnh (rewrite_query) — rơi về câu
    # gốc khi không có lịch sử hội thoại (rewrite_query bỏ qua bước viết lại).
    query = state.get("standalone_query") or state["query"]

    try:
        # Client Chroma là sync; bọc run_in_threadpool để không chẹn event
        # loop của FastAPI khi có nhiều request /chat đồng thời.
        results = await run_in_threadpool(
            store.similarity_search_with_score, query, k=settings.rag_top_k
        )
    except Exception as exc:
        # Lỗi hạ tầng (embeddings/Chroma), khác với "không tìm thấy tài liệu
        # phù hợp" — route phải trả 503, không phải câu từ chối thông thường.
        raise RetrievalError("Không gọi được embeddings hoặc Chroma") from exc

    # Chroma cấu hình cosine distance: càng nhỏ càng liên quan. Loại chunk
    # vượt ngưỡng thay vì đưa context không liên quan cho LLM.
    relevant = [doc for doc, score in results if score <= settings.rag_max_distance]

    retrieved = [
        {
            "content": doc.page_content,
            "document_id": doc.metadata["document_id"],
            "title": doc.metadata["title"],
            "source_type": doc.metadata["source_type"],
        }
        for doc in relevant
    ]

    seen: set[int] = set()
    sources: list[dict[str, Any]] = []
    for chunk in retrieved:
        if chunk["document_id"] in seen:
            continue
        seen.add(chunk["document_id"])
        sources.append(
            {
                "document_id": chunk["document_id"],
                "title": chunk["title"],
                "snippet": _snippet(chunk["content"]),
                "source_type": chunk["source_type"],
            }
        )

    return {"retrieved": retrieved, "sources": sources}
