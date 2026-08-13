"""Node `rewrite_query` — viết lại câu hỏi mới nhất thành độc lập ngữ cảnh.

Chỉ chạy phần việc thật khi `chat_history` không rỗng — câu hỏi đầu tiên của
một cuộc hội thoại luôn tự đủ nghĩa, viết lại chỉ tốn thêm một lệnh gọi LLM
vô ích (đúng nguyên tắc đã áp cho `faq_lookup`/embed-once trong docs: chỉ trả
chi phí khi thật sự cần).

Tách hẳn khỏi `generate`: lịch sử hội thoại chỉ được dùng để VIẾT LẠI CÂU HỎI
truy vấn, không bao giờ được đưa thẳng vào prompt trả lời — `generate` vẫn
chỉ được phép trả lời dựa trên tài liệu đã truy xuất (bảo đảm #2 của thiết
kế, xem generate.py). Nếu để lịch sử rò vào generate, model có thể "nhớ" và
bịa dựa trên câu trả lời cũ thay vì tài liệu thật.
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import ChatState
from src.services.llm import get_chat_llm

_SYSTEM_PROMPT = (
    "Rewrite the LATEST user question into a standalone question that makes "
    "full sense on its own with NO conversation history attached — someone "
    "reading only your rewritten question, with no other context, must be "
    "able to tell exactly what topic/item it refers to.\n\n"
    "Using the conversation history below, REPLACE every pronoun, ellipsis, "
    "or implicit reference (it, that one, what about X, còn ... thì sao) "
    "with the specific noun/topic it refers to. Do not just drop the "
    "pronoun — substitute it. Do NOT answer the question. Do NOT add any "
    "information not implied by the history. If the latest question already "
    "names its own topic explicitly, return it unchanged.\n\n"
    "Example:\n"
    "History — User: Làm thẻ xe cần giấy tờ gì? / Assistant: Cần CCCD và cà "
    "vẹt xe.\n"
    "Latest question: Thẻ nó có mất phí không?\n"
    "Correct rewrite: Thẻ xe có mất phí không?\n"
    "Wrong rewrite (do not do this — drops the topic): Có mất phí không?\n\n"
    "Output ONLY the rewritten question in Vietnamese (tiếng Việt) — no "
    "explanation, no quotes."
)


def _format_history(history: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for turn in history:
        lines.append(f"User: {turn['question']}")
        lines.append(f"Assistant: {turn['answer']}")
    return "\n".join(lines)


async def rewrite_query_node(state: ChatState) -> dict[str, Any]:
    """Viết lại `query` thành `standalone_query` nếu có lịch sử hội thoại."""
    history = state.get("chat_history") or []
    if not history:
        return {"standalone_query": state["query"]}

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"CONVERSATION HISTORY:\n{_format_history(history)}\n\n"
                f"LATEST QUESTION: {state['query']}"
            )
        ),
    ]

    try:
        response = await get_chat_llm().ainvoke(messages)
    except Exception:
        # Lỗi viết lại không được chặn cả pipeline — dùng tạm câu hỏi gốc.
        # Retrieval có thể kém chính xác hơn với câu mơ hồ, nhưng vẫn chạy
        # được thay vì hỏng toàn bộ request vì một bước phụ trợ.
        return {"standalone_query": state["query"]}

    rewritten = (response.content or "").strip()
    return {"standalone_query": rewritten or state["query"]}
