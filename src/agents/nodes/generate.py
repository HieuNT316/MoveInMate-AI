"""Node `generate` — docs/architecture_diagram.md mục 3.4.

Guard chống bịa có **hai tầng**, cùng một kết quả:

1. `retrieved` rỗng → không gọi LLM, trả câu từ chối cố định.
2. Có tài liệu nhưng LLM tự nhận không trả lời được → cũng đổi thành câu từ
   chối, `answer_source="no_context"`, **và bỏ `sources`**.

Tầng 2 thêm ngày 25/08 (V3/B5). Trước đó chỉ có tầng 1, nên câu hỏi "đúng lĩnh
vực nhưng KB không có dữ liệu" trả về `answer_source="rag"` kèm nguyên khối
trích dẫn ngay dưới câu "tôi không tìm thấy thông tin" — đo được **0/3** ở
`eval/results/report.md` mục 2, và charter mục 11 xếp đây là *"chế độ hỏng nguy
hiểm nhất còn lại"*: câu hỏi nghe hợp lệ, trích dẫn trông đáng tin, người dùng
không có cách nào biết hệ thống đang không biết.
"""

import unicodedata
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src.agents.state import ChatState
from src.agents.tools.navigation import request_submission_navigation
from src.services.llm import get_chat_llm

REFUSAL = (
    "Xin lỗi, tôi chưa tìm thấy thông tin này trong tài liệu hiện có. "
    "Bạn vui lòng liên hệ Ban quản lý toà nhà để được hỗ trợ chính xác."
)

# LLM phát ra đúng chuỗi này khi tài liệu không đủ để trả lời. Có một mã quy
# ước để nhận diện thì chắc chắn hơn hẳn đoán ý từ câu chữ tự do — cùng lý do
# `sources[]` sinh tất định thay vì hỏi LLM tự liệt kê.
NO_ANSWER_SENTINEL = "KHONG_CO_TRONG_TAI_LIEU"

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
    "numbers or conditions not present in the documents. Keep answers short "
    "and to the point. Do NOT list sources/citations yourself — the system "
    "attaches them separately.\n\n"
    "If the DOCUMENTS do not contain what the user asked for, reply with "
    f"EXACTLY this and nothing else: {NO_ANSWER_SENTINEL}\n"
    "Use it whenever you would otherwise write 'I could not find', 'the "
    "documents do not mention', or any similar admission. Do NOT soften it, "
    "do NOT add an apology, do NOT add a partial answer alongside it. If you "
    "CAN answer even part of the question from the documents, answer that "
    "part normally instead of using the marker.\n\n"
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


# Lưới bắt dự phòng cho những lượt LLM không chịu dùng mã quy ước. Cố ý hẹp:
# chỉ những cách nói thẳng ra là KHÔNG TÌM ĐƯỢC. Không đưa vào đây các cụm như
# "tài liệu không yêu cầu…" hay "không cần công chứng" — đó là câu trả lời có
# nội dung, chặn nhầm còn tệ hơn để lọt.
_REFUSAL_PHRASES = (
    "khong tim thay", "chua tim thay", "khong co thong tin",
    "khong de cap", "khong duoc de cap", "khong noi ro",
    "khong the tra loi", "khong tra loi duoc", "khong cung cap thong tin",
)

# Câu từ chối thật thì ngắn. Một câu trả lời DÀI có chứa "không đề cập" gần như
# luôn là trả lời được một phần ("Tài liệu không đề cập phí X, nhưng có nêu Y")
# — đổi nó thành từ chối là vứt mất phần Y người dùng cần.
_REFUSAL_MAX_LEN = 220


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(
        c for c in decomposed if unicodedata.category(c) != "Mn"
    ).replace("đ", "d")


def _is_refusal(answer: str) -> bool:
    """Câu trả lời này thật ra là "tôi không biết" phải không?

    Ưu tiên mã quy ước; câu chữ tự do chỉ là lưới bắt dự phòng, và chỉ tính khi
    câu đủ ngắn để chắc chắn không kèm nội dung thật.
    """
    if NO_ANSWER_SENTINEL in answer:
        return True
    folded = _fold(answer)
    return len(answer) <= _REFUSAL_MAX_LEN and any(p in folded for p in _REFUSAL_PHRASES)


REFUSAL_WITH_TICKET = (
    "Xin lỗi, tôi chưa tìm thấy thông tin này trong tài liệu hiện có. "
    "Bạn có muốn gửi câu hỏi này cho Ban quản lý để được trả lời không?"
)


def _refuse(ticket_worthy: bool = False) -> dict[str, Any]:
    """Câu từ chối chuẩn — và **bỏ `sources`**.

    Bỏ nguồn là nửa quan trọng hơn: hiện khối "Nguồn trích dẫn" ngay dưới một
    câu "tôi không biết" là kiểu hiển thị gây hiểu nhầm nhất, vì trích dẫn làm
    câu trả lời trông đáng tin đúng lúc nó rỗng nội dung.

    `sources` do `rag_retrieve` đặt vào state; trả `[]` ở đây để ghi đè.

    `ticket_worthy` — có nên mời cư dân gửi câu hỏi cho BQL không (US-11).
    **Không phải lúc nào từ chối cũng đáng mở ticket**, và ranh giới đã có sẵn
    trong chính cấu trúc hai tầng của guard:

    | Tầng | Nghĩa | Ví dụ trong bộ eval | Ticket? |
    |---|---|---|---|
    | 1 · `retrieved` rỗng | Không đoạn nào đủ gần ngưỡng → câu ngoài lĩnh vực | giá vàng, thời tiết, nấu phở (4/4 chặn ở đây) | **Không** |
    | 2 · có tài liệu, LLM nói không có | Đúng lĩnh vực nhưng KB thiếu dữ liệu | Q33-35 "phí bảo trì 2%…" | **Có** |

    Mời mở ticket cho câu "cho tôi công thức nấu phở bò" thì vừa vô duyên vừa
    làm ngập hộp thư BQL bằng những câu họ không có trách nhiệm trả lời. Còn
    tầng 2 lại đúng là những câu BQL trả lời được và nên biết là cư dân đang
    hỏi — mỗi ticket ở đó là một chỗ trống trong KB tự báo cáo về.
    """
    if ticket_worthy:
        # Không tự tạo ticket ở đây: graph không chạm DB (xem state.py), và
        # quan trọng hơn — tạo ngầm mỗi lần AI bí là đẩy rác vào hàng đợi của
        # BQL. Chỉ phát tín hiệu; cư dân bấm đồng ý thì FE gọi POST /tickets.
        return {
            "answer": REFUSAL_WITH_TICKET,
            "answer_source": "no_context",
            "sources": [],
            "ticket_suggested": True,
        }
    return {
        "answer": REFUSAL,
        "answer_source": "no_context",
        "sources": [],
        "ticket_suggested": False,
    }


async def generate_node(state: ChatState) -> dict[str, Any]:
    """Sinh câu trả lời từ context đã truy xuất, hoặc từ chối nếu rỗng.

    Guard chống bịa (bảo đảm #2 của thiết kế): không có `retrieved` thì
    KHÔNG gọi LLM, trả câu từ chối cố định — ràng buộc trong code, không phải
    lời dặn trong prompt.
    """
    retrieved = state.get("retrieved", [])
    if not retrieved:
        return _refuse()

    llm = get_chat_llm().bind_tools(_TOOLS)
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=f"DOCUMENTS:\n{_build_context(retrieved)}\n\nQUESTION: {state['query']}"
        ),
    ]

    try:
        response = await llm.ainvoke(messages)
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None
    except Exception:
        # Lỗi một phần: đã truy xuất được context (sources đã có trong state
        # từ rag_retrieve) nhưng LLM lỗi/timeout — trả kèm sources thay vì
        # thất bại toàn bộ request (docs mục 5).
        return {"answer": GENERATION_FAILED_NOTE, "answer_source": "rag",
                "usage": None}

    if not response.tool_calls:
        # `usage` đi kèm cả nhánh từ chối: lượt gọi LLM đã xảy ra và đã tốn
        # token thật, cost tracking phải đếm nó. Không đếm thì hoá đơn thiếu
        # đúng những lượt tệ nhất — hỏi mà không trả lời được.
        usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}

        # Tầng 2 của guard: có tài liệu, nhưng tài liệu không chứa câu trả lời.
        # Đúng lĩnh vực mà KB thiếu dữ liệu — chỗ duy nhất đáng mời mở ticket.
        if _is_refusal(str(response.content)):
            return {**_refuse(ticket_worthy=True), "usage": usage}
        return {"answer": response.content, "answer_source": "rag", "usage": usage}

    # Tool thuần, không tác dụng phụ — chạy trực tiếp, không cần sandbox.
    tool_call = response.tool_calls[0]
    suggested_action = request_submission_navigation.invoke(tool_call["args"])

    messages += [response, ToolMessage(content=str(suggested_action), tool_call_id=tool_call["id"])]
    try:
        final = await llm.ainvoke(messages)
        final_usage = getattr(final, "usage", None)
        final_input = getattr(final_usage, "prompt_tokens", None) if final_usage else None
        final_output = getattr(final_usage, "completion_tokens", None) if final_usage else None
    except Exception:
        return {
            "answer": NAVIGATION_FOLLOWUP_FAILED_NOTE,
            "answer_source": "rag",
            "suggested_action": suggested_action,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        }

    # Cố ý KHÔNG kiểm từ chối ở nhánh này: LLM đã gọi tool điều hướng nghĩa là
    # nó nhận ra đúng một thủ tục, câu chốt ở đây là lời mời bấm nút chứ không
    # phải câu trả lời tra cứu. `_refuse()` sẽ xoá mất `suggested_action` —
    # đánh đổi sai chỗ, vì lớp điều hướng tất định đã phải trả giá mới có
    # (đo 0/5 khi còn phụ thuộc LLM gọi tool, xem routes.py).
    # Merge: first call + second call token counts
    merged_input = (input_tokens or 0) + (final_input or 0)
    merged_output = (output_tokens or 0) + (final_output or 0)
    return {
        "answer": final.content, "answer_source": "rag",
        "suggested_action": suggested_action,
        "usage": {"input_tokens": merged_input, "output_tokens": merged_output},
    }
