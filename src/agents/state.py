from __future__ import annotations

from typing import Any, TypedDict


class ChatState(TypedDict, total=False):
    """State cho `chat_graph` (docs/architecture_diagram.md mục 3.4).

    total=False: mỗi node chỉ ghi phần mình phụ trách, field còn lại chưa tồn
    tại ở bước trước đó không phải là lỗi.
    """

    query: str
    # [{"question": str, "answer": str}] — N lượt gần nhất của CÙNG cuộc hội
    # thoại, route đọc từ DB trước khi gọi graph. Chỉ dùng để viết lại câu hỏi
    # (`rewrite_query`) — KHÔNG đưa thẳng vào generate, để generate vẫn chỉ
    # được phép trả lời từ tài liệu truy xuất (giữ nguyên bảo đảm chống bịa).
    chat_history: list[dict[str, str]]
    # [{"faq_id": int, "question": str, "answer": str}] — FAQ đang bật, route
    # đọc từ DB trước khi gọi graph, y như `chat_history`.
    #
    # Truyền VÀO thay vì để node tự mở session: graph không chạm DB (xem
    # `suggested_action` ở dưới — cùng lý do). Giữ được thì node test bằng dữ
    # liệu tiêm vào, không cần DB, và vai AI làm xong trước khi vai BE có
    # `store.get_active_faqs`.
    faqs: list[dict[str, Any]]
    # Câu hỏi đã viết lại thành độc lập ngữ cảnh — rag_retrieve dùng field này
    # nếu có, rơi về `query` gốc nếu rewrite_query bỏ qua (không có lịch sử).
    standalone_query: str
    # faq_id đã khớp — route dùng để đếm lượt xem. None/absent = không khớp FAQ nào.
    matched_faq_id: int | None
    # [{"content": str, "document_id": int, "title": str, "source_type": str}]
    # — chunk thô lấy từ Chroma, dùng để build prompt cho generate.
    retrieved: list[dict[str, Any]]
    # [{"document_id": int, "title": str, "snippet": str, "source_type": str}]
    # — đã gộp theo document_id, đúng shape trả về cho FE (schemas.Source).
    sources: list[dict[str, Any]]
    answer: str
    answer_source: str
    # {"type": "navigate_to_submission", "procedure_name": str} — do generate
    # phát ra khi LLM gọi tool `request_submission_navigation`. Chưa có
    # checklist_item_id ở đây vì graph không chạm DB; route resolve tiếp.
    suggested_action: dict[str, str] | None
    # US-11 — câu hỏi ĐÚNG LĨNH VỰC mà KB không có dữ liệu, đáng mời cư dân
    # gửi cho BQL. Chỉ là tín hiệu: graph không tạo ticket (không chạm DB), và
    # tạo ngầm mỗi lần AI bí sẽ đẩy rác vào hàng đợi BQL. Xem `generate._refuse`.
    ticket_suggested: bool
