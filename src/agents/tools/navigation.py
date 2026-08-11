"""Tool điều hướng người dùng đến nơi nộp hồ sơ cho một thủ tục cụ thể.

Tool KHÔNG có tác dụng phụ — không gọi DB, không gọi API nào. Nó chỉ là tín
hiệu có cấu trúc để LLM "khai báo" ý định điều hướng, thay vì tự bịa định
dạng điều hướng trong văn xuôi (cùng triết lý với `sources[]`: quyết định gì
tất định được thì không giao cho LLM tự do diễn đạt).

`procedure_name` là tên tự nhiên do LLM suy ra, CHƯA chắc khớp chữ với
`task_name` trong CHECKLIST_ITEMS. Việc đối chiếu ra `checklist_item_id`
thật nằm ở `src/api/routes.py`, không phải ở đây — graph không được chạm DB
(docs/architecture_diagram.md mục 7: rule engine/dữ liệu là service thuần,
tách khỏi LangGraph).
"""

from langchain_core.tools import tool


@tool
def request_submission_navigation(procedure_name: str) -> dict[str, str]:
    """Use when the user asks HOW TO SUBMIT documents/paperwork for a specific procedure.

    Different from asking "what documents are needed" (that's a regular
    information question — do NOT call this tool for that). Only use this
    tool when the user wants to know WHERE/HOW to submit and could be
    navigated there in the app.

    ONLY call this when you have identified EXACTLY ONE specific procedure
    from the question and retrieved documents. If the question is generic or
    could match several procedures, do NOT call this tool — ask the user
    which procedure they mean, directly in your regular text answer.

    Args:
        procedure_name: The procedure name in VIETNAMESE (always Vietnamese,
            even though this instruction is in English), phrased the way it
            appears in the documents/checklist (e.g. "Đăng ký thẻ cư dân",
            "Đăng ký thẻ xe") — used to match against the user's real
            checklist.
    """
    return {"type": "navigate_to_submission", "procedure_name": procedure_name}
