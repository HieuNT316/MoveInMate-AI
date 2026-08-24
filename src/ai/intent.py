"""Nhận ý định làm thủ tục từ câu người dùng gõ — 3 lớp: keyword, fuzzy, LLM.

Trước cả ba lớp là một **cổng tất định** (`wants_to_act`): câu hỏi THÔNG TIN
("Làm thẻ xe cần giấy tờ gì?") không bao giờ được vào luồng điền form, dù tên
thủ tục có nằm nguyên trong câu. Thiếu cổng này thì mọi câu hỏi thường bị nuốt
vào form và US-05 (hỏi đáp kèm nguồn) ngừng hoạt động — xem `_INFO_TAILS`.

Cổng còn là chỗ giữ chi phí: LLM ở lớp 3 chỉ được gọi khi câu nói có dấu hiệu
HÀNH ĐỘNG, nên câu hỏi thông tin không tốn thêm lượt gọi nào.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Literal, NamedTuple

from sqlalchemy.orm import Session

from src.models.db import ChecklistItem
from src.services.llm import get_chat_llm

logger = logging.getLogger("moveinmate")

# Stopwords — từ quá chung không phân biệt được thủ tục. "the" (thẻ),
# "xe", "ki", "lam" xuất hiện trong hầu hết task names, dùng chúng làm
# keyword sẽ gây false positive. "dang" (đăng) KHÔNG stopword vì nó phân biệt
# được "đăng ký" vs "làm" — hai hành động khác nhau trong cùng ngữ cảnh.
_STOPWORDS = frozenset([
    "cua", "va", "hoac", "voi", "cho", "nay", "kia", "cac",
    "la", "co", "khong", "duoc", "de", "ve", "qua", "tai",
    "tu", "trong", "nhung", "cac", "mot", "h nay", "h kia",
    "lam", "ki", "the", "xe", "nha", "phong", "be",
    "thang", "cu", "dan", "tru", "chinh", "giao",
])


# Ranh giới ý định — bản gốc nằm ở `src/api/routes.py` để gắn nút điều hướng,
# chuyển về đây làm nơi duy nhất giữ vốn từ nhận ý định (vai AI). `routes.py`
# import lại từ đây, không giữ bản sao: hai danh sách trôi lệch nhau thì nút
# điều hướng và luồng điền form sẽ hiểu cùng một câu theo hai kiểu khác nhau.
#
# Phải có cả hai danh sách. Chỉ bắt động từ hành động là chưa đủ: "Làm thẻ xe
# cần giấy tờ gì?" có "làm thẻ" nhưng đuôi câu cho thấy người ta chỉ đang hỏi.
_ACTION_MARKERS = (
    "nop ", "nop ho so", "dan toi", "dua toi", "cho toi nop", "giup toi nop",
    "toi muon lam", "toi muon dang ky", "muon nop", "can nop", "toi nop",
)
_INFO_TAILS = (
    "can giay to gi", "can gi", "gom nhung gi", "gom gi", "la gi",
    "bao nhieu", "the nao", "ra sao", "mat bao lau", "khi nao", "thu tuc gi",
)

# Chuỗi LLM phải trả về khi không thủ tục nào khớp. Trả nguyên văn chuỗi này
# là cách duy nhất LLM nói "không biết" — mọi câu chữ khác đều bị coi là không
# khớp, xem `_llm_pick_procedure`.
_NO_MATCH = "khong_khop"


class ProcedureMatch(NamedTuple):
    """Kết quả nhận ý định.

    Ba trạng thái, phân biệt bằng `item` và `ambiguous`:

    - `item` có giá trị → vào luồng điền form của đúng thủ tục đó.
    - `item=None, ambiguous=True` → khớp nhiều thủ tục, phải hỏi lại người dùng.
    - `item=None, ambiguous=False` → **không phải ý định làm thủ tục**, nhường
      cho RAG trả lời. Đây là trạng thái bắt buộc phải có: thiếu nó thì mọi câu
      hỏi thường đều rơi vào nhánh hỏi-lại và người dùng không bao giờ hỏi được
      thông tin gì.
    """

    item: ChecklistItem | None
    confidence: Literal["high", "medium", "low"]
    ambiguous: bool = False
    disambiguation_options: list[ChecklistItem] = []


_NOT_A_PROCEDURE = ProcedureMatch(item=None, confidence="low", ambiguous=False)


def _normalize(text: str) -> str:
    """Bo dau tieng Viet, chuyen thanh lowercase."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(
        c for c in decomposed
        if unicodedata.category(c) != "Mn"
    ).replace("đ", "d")


def _extract_keywords(text: str) -> list[str]:
    """Tach tu khoa 3+ ky tu (sau khi bo dau), loai bo stopwords."""
    norm = _normalize(text)
    words = re.findall(r"\b\w{3,}\b", norm)
    return [w for w in words if len(w) >= 3 and w not in _STOPWORDS]


def _task_name_contains(task_name: str, keyword: str) -> bool:
    """So khớp keyword trong task_name, Unicode-normalized de xu ly tieng Viet."""
    return keyword in _normalize(task_name)


def _has_form(item: ChecklistItem) -> bool:
    """True khi item co form_schema (khong None).

    Luc nay dien ra trong Python sau ORM hydration, dam bao hoat dong
    nhat ky tren moi dialect (vi du SQLite luu None cua JSON thanh chuoi
    'null' trong cot, khong phai SQL NULL).
    """
    return item.form_schema is not None


def is_info_question(message: str) -> bool:
    """True khi câu là HỎI VỀ thủ tục, không phải ý định LÀM nó."""
    return any(tail in _normalize(message) for tail in _INFO_TAILS)


def has_action_marker(message: str) -> bool:
    """True khi câu có dấu hiệu muốn thực hiện thủ tục ("cho tôi nộp…")."""
    return any(marker in _normalize(message) for marker in _ACTION_MARKERS)


def wants_to_act(message: str) -> bool:
    """True khi câu là ý định LÀM thủ tục, không phải hỏi về nó.

    Giữ nguyên ngữ nghĩa bản cũ ở `routes.py` để nút điều hướng không đổi
    hành vi khi chuyển sang import từ đây.
    """
    return not is_info_question(message) and has_action_marker(message)


async def _llm_pick_procedure(message: str, form_items: list[ChecklistItem]) -> ChecklistItem | None:
    """Lớp 3 — hỏi LLM xem câu nói khớp thủ tục nào, hoặc không thủ tục nào.

    Kết quả của LLM **không được tin thẳng**: chỉ nhận khi chuỗi trả về trùng
    khít tên một thủ tục có thật trong `form_items`. Cùng lập luận đã áp cho
    `sources[]` và cho lớp đối chiếu điều hướng — việc gì tính tất định được
    thì không giao cho LLM quyết. LLM ở đây chỉ được phép *chọn* trong danh
    sách đóng, không được phép *đặt tên*.

    Lỗi mạng/timeout trả None: không nhận ra ý định làm thủ tục thì cùng lắm
    người dùng nhận câu trả lời RAG thông thường, còn ném lỗi thì hỏng cả
    `/chat`.
    """
    names = [item.task_name for item in form_items]
    listing = "\n".join(f"- {name}" for name in names)
    prompt = (
        "Bạn phân loại ý định của cư dân trong ứng dụng thủ tục nhận nhà.\n\n"
        f"Danh sách thủ tục có thể nộp hồ sơ:\n{listing}\n\n"
        f'Câu của cư dân: "{message}"\n\n'
        "Cư dân có đang muốn NỘP HỒ SƠ / THỰC HIỆN đúng một thủ tục trong danh "
        "sách trên không?\n"
        "- Nếu có: trả về CHÍNH XÁC tên thủ tục đó, chép nguyên văn từ danh "
        "sách, không thêm chữ nào khác.\n"
        f"- Nếu không, hoặc không chắc, hoặc cư dân chỉ đang HỎI THÔNG TIN về "
        f"thủ tục: trả về đúng chuỗi {_NO_MATCH}\n\n"
        "Chỉ trả về một dòng duy nhất, không giải thích."
    )

    try:
        response = await get_chat_llm().ainvoke(prompt)
    except Exception:
        logger.warning("intent_llm_failed", exc_info=True)
        return None

    answer = str(response.content).strip().strip('"').strip()
    if answer == _NO_MATCH:
        return None
    for item in form_items:
        if item.task_name == answer:
            return item
    # LLM trả chữ lạ (bịa tên, thêm lời dẫn, đổi hoa thường) — coi như không khớp.
    logger.info("intent_llm_unrecognised_answer", extra={"llm_answer": answer[:120]})
    return None


async def detect_procedure_intent(message: str, db: Session) -> ProcedureMatch:
    """Nhận ý định làm thủ tục: cổng tất định → keyword → fuzzy → LLM.

    Trả `_NOT_A_PROCEDURE` cho mọi câu không phải ý định làm thủ tục, để
    `/chat` rơi xuống RAG như cũ.
    """
    # Cổng tất định, đứng trước cả lớp 1: câu hỏi thông tin không bao giờ vào
    # luồng form. Không có bước này thì "Đăng ký thẻ xe cần giấy tờ gì?" bị lớp
    # 2 nuốt (tên thủ tục nằm nguyên trong câu) và người dùng nhận về một form
    # thay vì câu trả lời.
    if is_info_question(message):
        return _NOT_A_PROCEDURE

    norm = _normalize(message)
    keywords = _extract_keywords(message)

    # Lớp 1: Keyword exact — so sánh trong Python de dam bao Unicode normalization
    # chính xác. SQLite ILIKE khong nhan Unicode decomposition.
    # Filter tai DB level thay vi load het roi filter: tranh bottleneck khi so
    # procedures tang, giam database load.
    form_items = db.query(ChecklistItem).filter(
        ChecklistItem.form_schema.isnot(None)
    ).all()
    for kw in keywords:
        candidates = [item for item in form_items if _task_name_contains(item.task_name, kw)]
        if len(candidates) == 1:
            return ProcedureMatch(item=candidates[0], confidence="high")

    # Lớp 2: Fuzzy
    candidates = [
        item for item in form_items
        if _normalize(item.task_name) in norm
    ]
    if len(candidates) == 1:
        return ProcedureMatch(item=candidates[0], confidence="medium")
    if len(candidates) > 1:
        return ProcedureMatch(
            item=None, confidence="low",
            ambiguous=True,
            disambiguation_options=candidates
        )

    # Lớp 3: LLM — chỉ chạy khi câu có dấu hiệu hành động, để câu hỏi thông
    # thường không phải trả tiền cho một lượt gọi LLM mà chắc chắn không khớp.
    if not form_items or not has_action_marker(message):
        return _NOT_A_PROCEDURE

    item = await _llm_pick_procedure(message, form_items)
    if item is not None:
        return ProcedureMatch(item=item, confidence="low")
    return _NOT_A_PROCEDURE
