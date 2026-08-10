"""Node `generate` — docs/architecture_diagram.md mục 3.4."""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src.agents.state import ChatState
from src.agents.tools.navigation import request_submission_navigation
from src.services.llm import get_chat_llm

REFUSAL = (
    "Xin lỗi, tôi chưa tìm thấy thông tin này trong tài liệu hiện có. "
    "Bạn vui lòng liên hệ Ban quản lý toà nhà để được hỗ trợ chính xác."
)

GENERATION_FAILED_NOTE = (
    "Tôi tìm thấy tài liệu liên quan bên dưới nhưng chưa thể tạo tóm tắt lúc "
    "này. Bạn xem trực tiếp nguồn trích dẫn hoặc thử lại sau ít phút."
)

NAVIGATION_FOLLOWUP_FAILED_NOTE = (
    "Bạn có thể nộp hồ sơ cho thủ tục này trong mục Checklist của app."
)

_TOOLS = [request_submission_navigation]

_SYSTEM_PROMPT = (
    "You are the MoveInMate assistant, helping new residents at Vinhomes "
    "Smart City complete move-in procedures. Answer ONLY using the DOCUMENTS "
    "provided below — no outside knowledge, no guessing, and never add "
    "numbers or conditions not present in the documents. If the documents "
    "are not enough to answer, say clearly that you could not find the "
    "information instead of guessing. Keep answers short and to the point. "
    "Do NOT list sources/citations yourself — the system attaches them "
    "separately.\n\n"
    "If the user asks HOW TO SUBMIT documents/paperwork for a specific "
    "procedure (different from asking what documents are needed) and you "
    "can identify exactly one procedure, call the "
    "`request_submission_navigation` tool, and also write an answer asking "
    "whether the user wants to be taken there. If it's not clear which "
    "procedure, do NOT call the tool — ask the user which procedure they "
    "mean instead.\n\n"
    "MANDATORY: Always write your answer to the user in Vietnamese (tiếng "
    "Việt), regardless of the language of these instructions or of the "
    "documents."
)


def _build_context(retrieved: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"[Document {i}] {chunk['title']}\n{chunk['content']}"
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

    llm = get_chat_llm().bind_tools(_TOOLS)
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=f"DOCUMENTS:\n{_build_context(retrieved)}\n\nQUESTION: {state['query']}"
        ),
    ]

    try:
        response = await llm.ainvoke(messages)
    except Exception:
        # Lỗi một phần: đã truy xuất được context (sources đã có trong state
        # từ rag_retrieve) nhưng LLM lỗi/timeout — trả kèm sources thay vì
        # thất bại toàn bộ request (docs mục 5).
        return {"answer": GENERATION_FAILED_NOTE, "answer_source": "rag"}

    if not response.tool_calls:
        return {"answer": response.content, "answer_source": "rag"}

    # Tool thuần, không tác dụng phụ — chạy trực tiếp, không cần sandbox.
    tool_call = response.tool_calls[0]
    suggested_action = request_submission_navigation.invoke(tool_call["args"])

    messages += [response, ToolMessage(content=str(suggested_action), tool_call_id=tool_call["id"])]
    try:
        final = await llm.ainvoke(messages)
    except Exception:
        return {
            "answer": NAVIGATION_FOLLOWUP_FAILED_NOTE,
            "answer_source": "rag",
            "suggested_action": suggested_action,
        }

    return {"answer": final.content, "answer_source": "rag", "suggested_action": suggested_action}
