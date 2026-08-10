"""Node `generate` — docs/architecture_diagram.md mục 3.4."""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import ChatState
from src.services.llm import get_chat_llm

REFUSAL = (
    "Xin lỗi, tôi chưa tìm thấy thông tin này trong tài liệu hiện có. "
    "Bạn vui lòng liên hệ Ban quản lý toà nhà để được hỗ trợ chính xác."
)

GENERATION_FAILED_NOTE = (
    "Tôi tìm thấy tài liệu liên quan bên dưới nhưng chưa thể tạo tóm tắt lúc "
    "này. Bạn xem trực tiếp nguồn trích dẫn hoặc thử lại sau ít phút."
)

_SYSTEM_PROMPT = (
    "Bạn là trợ lý MoveInMate, hỗ trợ cư dân mới tại Vinhomes Smart City hoàn "
    "thành thủ tục nhận nhà. CHỈ trả lời dựa trên phần TÀI LIỆU được cung cấp "
    "bên dưới — không dùng kiến thức ngoài, không suy đoán, không tự thêm số "
    "liệu hay điều kiện không có trong tài liệu. Nếu tài liệu không đủ để trả "
    "lời, hãy nói rõ là không tìm thấy thay vì đoán. Trả lời ngắn gọn, đúng "
    "trọng tâm, bằng tiếng Việt. KHÔNG tự liệt kê nguồn/trích dẫn trong câu "
    "trả lời — hệ thống đã đính kèm nguồn riêng."
)


def _build_context(retrieved: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"[Tài liệu {i}] {chunk['title']}\n{chunk['content']}"
        for i, chunk in enumerate(retrieved, start=1)
    )


async def generate_node(state: ChatState) -> dict[str, Any]:
    """Sinh câu trả lời từ context đã truy xuất, hoặc từ chối nếu rỗng.

    Guard chống bịa (bảo đảm #2 của thiết kế): không có `retrieved` thì
    KHÔNG gọi LLM, trả câu từ chối cố định — ràng buộc trong code, không phải
    lời dặn trong prompt.
    """
    retrieved = state.get("retrieved", [])
    if not retrieved:
        return {"answer": REFUSAL, "answer_source": "no_context"}

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=f"TÀI LIỆU:\n{_build_context(retrieved)}\n\nCÂU HỎI: {state['query']}"
        ),
    ]

    try:
        response = await get_chat_llm().ainvoke(messages)
    except Exception:
        # Lỗi một phần: đã truy xuất được context (sources đã có trong state
        # từ rag_retrieve) nhưng LLM lỗi/timeout — trả kèm sources thay vì
        # thất bại toàn bộ request (docs mục 5).
        return {"answer": GENERATION_FAILED_NOTE, "answer_source": "rag"}

    return {"answer": response.content, "answer_source": "rag"}
