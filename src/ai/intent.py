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

# Động từ hành chính dùng thay cho nhau ("làm thẻ…" / "đăng ký thẻ…" / "xin cấp
# thẻ…" cùng chỉ một thủ tục) — bỏ đi để chỉ còn phần lõi mang tính phân biệt.
# Giữ khớp với `_ACTION_PREFIXES` ở `routes.py`, nơi đã dùng cùng cách này cho
# nút điều hướng từ 12/08.
_ACTION_PREFIXES = ("dang ky lam ", "dang ky ", "xin cap ", "xin ", "kich hoat ", "lam ")


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
    # Bổ sung 25/08 sau khi đo trên cả 37 câu `eval/questions.yaml` — mỗi
    # chuỗi dưới đây là một câu hỏi thật đã bị nhận nhầm thành ý định làm thủ
    # tục. Đều là từ để hỏi, nên không nuốt nhầm câu muốn hành động.
    "nhung gi", "lam sao", "o dau", "nao xu ly", "bao lau",
    "duoc khong", "co phai", "co duoc", "hay khong", "phai lam gi",
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


def _strip_action_prefix(text: str) -> str:
    for prefix in _ACTION_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix) :]
    return text


def _core_name(text: str) -> str:
    """Phần lõi của tên thủ tục: bỏ dấu, bỏ động từ đầu, bỏ phần trong ngoặc.

    `"Làm thẻ cư dân (chủ hộ)"` → `"the cu dan"`.

    Không có bước bỏ ngoặc thì lớp 2 so nguyên chuỗi và **"làm thẻ cư dân"
    không khớp được mục nào** — người dùng gõ đúng tên thủ tục mà hệ thống vẫn
    không nhận ra (đo được 25/08). `routes.py::_core_name` đã xử lý đúng như
    vậy cho nút điều hướng từ 12/08; đây là cùng một bài toán.
    """
    stripped = _strip_action_prefix(_normalize(text))
    return re.sub(r"\s*\([^)]*\)", "", stripped).strip()


def _has_form(item: ChecklistItem) -> bool:
    """True khi item có `form_schema` thật.

    **Phải lọc trong Python, sau khi ORM đã dựng đối tượng — đừng chuyển xuống
    SQL.** `JSONType` lưu `None` của Python thành chuỗi JSON `'null'`, không
    phải SQL NULL, nên `form_schema.isnot(None)` **đúng với mọi hàng** và
    không lọc được gì:

        SELECT task_name, form_schema, form_schema IS NULL
        → ('Ký nội quy', 'null', 0)          ← chuỗi 'null', IS NULL = false

    Đúng với cả SQLite lẫn Postgres: đây là cách `sqlalchemy.JSON` xử lý None
    (`none_as_null` mặc định False), không phải quirk của một dialect. Muốn lọc
    ở tầng DB thì phải khai `none_as_null=True` cho cột trước — là migration.

    Đã chuyển xuống SQL một lần ngày 24/08 (commit 8045c58, "M1") và hỏng:
    thủ tục không có form lọt vào vòng so khớp rồi tranh chỗ với thủ tục có
    form — "Cho tôi xem thời tiết Hà Nội" khớp `high` vào "Ký **nội** quy toà
    nhà". `test_loc_form_schema_phai_chay_trong_python` khoá lại chuyện này.

    Bảng chỉ khoảng chục hàng; lọc trong Python không phải nút thắt gì.
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

    # `_has_form` phải lọc trong Python — đọc docstring của nó trước khi định
    # chuyển bộ lọc này xuống câu query.
    all_items = db.query(ChecklistItem).all()
    form_items = [item for item in all_items if _has_form(item)]

    # Lớp 0 — khớp KHÍT cả tên thủ tục. Đứng trước mọi lớp khác vì nó không thể
    # nhầm: trùng nguyên tên thì chỉ có đúng một mục.
    #
    # ┌─ Vì sao có lớp này (25/08 — Thu đọc) ──────────────────────────────┐
    # │ Khi AI hỏi lại "bạn muốn thủ tục nào?", `web/app/chat/page.tsx`     │
    # │ dựng mỗi lựa chọn thành một nút, bấm nút thì gửi `task_name` làm    │
    # │ `message` (send(option.task_name)). Không có lớp 0 thì câu đó rơi   │
    # │ xuống lớp 2 — vốn so PHẦN LÕI, đã bỏ phần trong ngoặc — nên         │
    # │ "Làm thẻ cư dân (chủ hộ)" lại khớp cả hai nhánh chủ hộ/người thuê   │
    # │ và AI hỏi lại đúng câu vừa hỏi. **Vòng lặp không lối ra.**          │
    # │                                                                     │
    # │ Sửa ở backend nên FE không phải đổi gì: cứ gửi `task_name` như      │
    # │ đang làm. Hợp đồng `ChatRequest`/`ChatResponse` giữ nguyên.         │
    # └─────────────────────────────────────────────────────────────────────┘
    probe = _normalize(message).strip()
    for item in form_items:
        if _normalize(item.task_name).strip() == probe:
            return ProcedureMatch(item=item, confidence="high")
    # ┌─ Đã BỎ lớp "khớp một từ khoá đơn" — 25/08 ─────────────────────────┐
    # │ Lớp cũ: tách từ 3+ ký tự khỏi câu, từ nào nằm trong đúng MỘT tên    │
    # │ thủ tục thì chốt luôn `high confidence`. Đo trên cả 37 câu của       │
    # │ `eval/questions.yaml`: nó gây 11 trong 15 ca nhận nhầm, khớp toàn    │
    # │ từ vu vơ — "thue", "nguoi", "may", "hong", "dinh", "vao", "boi".     │
    # │                                                                     │
    # │ Nặng nhất: "Cho tôi công thức nấu PHỞ bò" → "pho" nằm lọt trong      │
    # │ "PHÒNG gym" → mở form đăng ký phòng gym. Đó đúng là câu demo bước 7  │
    # │ ("hỏi ngoài tài liệu → phải từ chối"), chỗ ăn điểm nhất theo         │
    # │ ROLES_AND_PLAN mục 8.                                               │
    # │                                                                     │
    # │ Nó còn không cứu được ca nào: FG01 "…thẻ XE MÁY…" bị "may" kéo về    │
    # │ "thẻ thang MÁY" — sai thủ tục. Bỏ lớp này thì lớp 2 khớp đúng.       │
    # │                                                                     │
    # │ Recall mất đi do bỏ lớp này (tên thủ tục dài hơn câu người ta gõ,    │
    # │ vd "Đăng ký internet và truyền hình") đã có lớp 3 LLM gánh — mà lớp  │
    # │ 3 chỉ chạy khi câu có dấu hiệu hành động, nên câu hỏi thường vẫn     │
    # │ không tốn lượt gọi nào.                                             │
    # └─────────────────────────────────────────────────────────────────────┘

    # Lớp 2: Fuzzy — so phần lõi, không so nguyên tên. Xem `_core_name`.
    probe_core = _core_name(message)
    candidates = [
        item for item in form_items
        if (core := _core_name(item.task_name))
        and (core == probe_core or core in probe_core)
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
