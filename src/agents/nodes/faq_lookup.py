"""Node `faq_lookup` — trả lời bằng FAQ do BQL soạn, trước khi động tới RAG.

Đặt trước `rag_retrieve` vì câu đã có người soạn sẵn đáp án thì không cần tra
tài liệu: nhanh hơn, rẻ hơn (không embed, không gọi LLM), và câu chữ do BQL
duyệt nên chính xác hơn bản LLM tóm tắt.

Đặt SAU `rewrite_query` chứ không phải đầu graph: câu tiếp nối ("còn phí thì
sao?") phải được viết lại thành câu độc lập trước, nếu không thì so với FAQ
bằng một câu thiếu chủ đề.

**Không chạm DB.** Danh sách FAQ do route đọc rồi truyền vào `ChatState.faqs`,
y như `chat_history`. Giữ được bất biến "graph không chạm DB" (xem
`src/agents/state.py`), và nhờ đó node test được bằng dữ liệu tiêm vào.

**Rỗng `faqs` thì node là no-op** — đúng trạng thái hiện tại của hệ thống
(bảng `faq` chưa có dữ liệu), nên bật nhánh này lên không đổi hành vi gì cho
tới khi có người soạn nội dung FAQ.
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.state import ChatState
from src.config import get_settings


def _words(text: str) -> set[str]:
    """Tập từ của câu — **giữ nguyên dấu, không bỏ stopword**.

    Hai lựa chọn này đều đi ngược trực giác thông thường, và đều do đo mà ra.
    So cùng một cặp câu bằng hai cách:

    | Câu người dùng | bỏ dấu + bỏ stopword | giữ dấu, giữ đủ từ |
    |---|---|---|
    | "Làm thẻ cư dân thế nào?"     | 1.000 | 0.857 |
    | "Mất thẻ cư dân thì làm sao?" | **0.667** | **0.400** |

    (FAQ đối chiếu: *"Làm thẻ cư dân như thế nào?"*)

    Câu thứ hai là câu hỏi **khác hẳn** — mất thẻ không phải làm thẻ. Ở ngưỡng
    0.5, bản bỏ dấu + bỏ stopword khớp cả hai, tức trả hướng dẫn *làm thẻ* cho
    người vừa *mất thẻ*. Bản này tách được.

    Vì sao: bỏ dấu làm "thẻ" và "thế" nhập một; bỏ stopword thì câu ngắn chỉ
    còn hai ba từ nên một từ khác biệt (mất/làm) không đủ kéo điểm xuống. Giữ
    đủ từ thì chính những từ khung câu lại là tín hiệu về cách hỏi, và mẫu số
    Jaccard phình ra đúng lúc hai câu thật sự khác nhau.

    Đánh đổi: gõ không dấu ("lam the cu dan") sẽ không khớp FAQ nào và rơi
    xuống RAG. Đó là chiều sai an toàn — RAG vẫn trả lời, lại còn kèm nguồn.
    """
    return set(re.findall(r"\w+", text.lower()))


def similarity(query: str, faq_question: str) -> float:
    """Độ trùng Jaccard giữa hai câu, tính theo TỪ. 0.0 → 1.0.

    So theo từ chứ không theo chuỗi con: tiếng Việt có rất nhiều từ ngắn lồng
    vào nhau ("phở" nằm trong "phòng" sau khi bỏ dấu), và so chuỗi con đúng là
    thứ đã làm cổng nhận ý định khớp bừa — xem `src/ai/intent.py`.
    """
    a, b = _words(query), _words(faq_question)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def best_match(query: str, faqs: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float]:
    """FAQ giống nhất và điểm của nó. Hoà điểm thì trả None — thà để RAG trả lời.

    Hoà nghĩa là câu hỏi mơ hồ giữa hai FAQ; chọn bừa một cái là đưa cư dân
    câu trả lời của một câu hỏi khác mà không có dấu hiệu gì để họ nhận ra.
    """
    if not faqs:
        return None, 0.0
    scored = sorted(
        ((faq, similarity(query, faq["question"])) for faq in faqs),
        key=lambda pair: pair[1],
        reverse=True,
    )
    best, top = scored[0]
    if len(scored) > 1 and scored[1][1] == top:
        return None, top
    return best, top


async def faq_lookup_node(state: ChatState) -> dict[str, Any]:
    """Trả lời từ FAQ nếu có câu đủ giống; không thì để state nguyên cho RAG.

    Ngưỡng `faq_min_similarity` cố ý đặt cao. Khớp lỏng ở đây tốn kém hơn vẻ
    ngoài: FAQ trả lời **không kèm trích dẫn**, nên mỗi lần cướp nhầm một câu
    mà RAG lẽ ra trả lời được là một lần cư dân mất phần nguồn tài liệu —
    trong khi "luôn kèm nguồn" chính là ràng buộc lõi của US-05.
    """
    faqs = state.get("faqs") or []
    if not faqs:
        return {}

    query = state.get("standalone_query") or state["query"]
    faq, score = best_match(query, faqs)
    if faq is None or score < get_settings().faq_min_similarity:
        return {}

    return {
        "answer": faq["answer"],
        "answer_source": "faq",
        # Câu trả lời do BQL soạn, không trích từ tài liệu nào — không có
        # `sources` để gắn. FE phân biệt bằng `answer_source="faq"` và nên ghi
        # rõ "Câu hỏi thường gặp" thay vì để trống chỗ nguồn trích dẫn.
        "sources": [],
        "matched_faq_id": faq["faq_id"],
    }
