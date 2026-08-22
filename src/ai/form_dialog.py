"""AI dẫn dắt cư dân điền hồ sơ — hỏi từng trường theo `form_schema`.

Thay cho việc bắt cư dân tự tìm form rồi tự điền: AI hỏi lần lượt từng trường
bằng đúng câu chữ đã soạn sẵn trong `form_schema.fields[i].question`, nhận câu
trả lời, kiểm tra tại chỗ, rồi hỏi trường tiếp theo. Hỏi hết thì dựng bản tóm
tắt để cư dân xem lại và sửa trước khi gửi.

**Không giữ trạng thái ở server.** Mỗi lượt, FE gửi lại `checklist_item_id` và
`form_data` đã thu được; backend suy ra "đang hỏi trường nào" bằng cách tìm
trường đầu tiên còn trống theo thứ tự khai trong schema. Chọn cách này vì hội
thoại có thể bị bỏ dở hàng giờ, và vì `POST /chat` đã là endpoint không trạng
thái — thêm một bảng phiên chỉ để nhớ con trỏ trường là chi phí không cần.

Ranh giới cố ý giữ: module này **không ghi gì vào DB**. Nó chỉ đọc `form_schema`
và trả `form_data` về cho FE; cư dân xác nhận rồi FE mới gọi `POST /applications`.
Người chốt hồ sơ vẫn là cư dân, không phải AI (spec mục 5.3).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal, NamedTuple

from sqlalchemy.orm import Session

from src.ai.intent import detect_procedure_intent
from src.models.db import ChecklistItem
from src.models.schemas import FormFieldSchema, FormSchemaPayload
from src.services import store

ChatIntent = Literal["qa", "form_generation", "form_review", "disambiguation"]

# Cách cư dân từ chối một trường không bắt buộc.
_SKIP_WORDS = frozenset([
    "khong", "khong co", "bo qua", "thoi", "khong can", "chua co", "-", "trong",
])

# Số viết bằng chữ — cư dân trả lời "hai cái" thường xuyên như gõ "2".
_NUMBER_WORDS = {
    "khong": 0, "mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5,
    "sau": 6, "bay": 7, "tam": 8, "chin": 9, "muoi": 10,
}


class FormTurn(NamedTuple):
    """Một lượt trong luồng điền hồ sơ, đã sẵn sàng trả về cho FE."""

    answer: str
    intent: ChatIntent
    checklist_item_id: int | None = None
    form_schema: FormSchemaPayload | None = None
    form_data: dict[str, str] | None = None
    options: list[ChecklistItem] | None = None


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(
        c for c in decomposed if unicodedata.category(c) != "Mn"
    ).replace("đ", "d").strip()


# --- Đọc câu trả lời vào một trường -------------------------------------


def _tidy_pattern_value(raw: str) -> str:
    """Dọn cách gõ trước khi so `pattern`: bỏ khoảng trắng, viết hoa.

    Biển số cư dân gõ "30a-12345" hay "30A 12345" là cùng một biển; bắt họ gõ
    lại chỉ vì hoa thường là kiểu chặt chẽ vô ích. Chỉ dọn khoảng trắng và hoa
    thường — không bỏ ký tự nào, để không âm thầm sửa dữ liệu người ta khai.
    """
    return re.sub(r"\s+", "", raw).upper()


def _read_number(raw: str) -> str | None:
    digits = re.search(r"\d+", raw)
    if digits:
        return digits.group()
    # Cư dân trả lời "hai cái" hay "hai thẻ" thường xuyên như gõ "2" — dò từng
    # từ chứ không so cả câu, nếu không thì chỉ mỗi "hai" trơ trọi mới nhận ra.
    for word in re.findall(r"\w+", _normalize(raw)):
        if word in _NUMBER_WORDS:
            return str(_NUMBER_WORDS[word])
    return None


def _read_select(field: FormFieldSchema, raw: str) -> str | None:
    """Khớp câu trả lời với một lựa chọn. Khớp nhiều lựa chọn thì coi như trượt.

    So khớp theo **ranh giới từ**, không phải chuỗi con. Lựa chọn tiếng Việt
    sau khi bỏ dấu thường rất ngắn ("Ô tô" → "o to") và đụng trúng giữa câu
    một cách tình cờ: "cho tôi nộp" chứa đúng chuỗi "o to". Dùng chuỗi con thì
    câu "cho tôi nộp hồ sơ thẻ xe máy" khớp cả "Ô tô" lẫn "Xe máy" và trường
    này âm thầm không điền được.
    """
    norm = _normalize(raw)
    matches = []
    for opt in field.options or []:
        opt_norm = _normalize(opt)
        if norm == opt_norm or re.search(rf"(?<!\w){re.escape(opt_norm)}(?!\w)", norm):
            matches.append(opt)
    return matches[0] if len(matches) == 1 else None


def apply_answer(field: FormFieldSchema, raw: str) -> tuple[str | None, str | None]:
    """Đọc câu trả lời vào một trường. Trả `(giá_trị, lỗi)` — đúng một cái khác None.

    Lỗi trả về là câu nói thẳng với cư dân, không phải mã lỗi: lượt sau AI sẽ
    đọc nguyên câu này rồi hỏi lại đúng trường đó.
    """
    raw = raw.strip()

    if not field.required and _normalize(raw) in _SKIP_WORDS:
        return field.default or "", None

    if field.type == "select":
        value = _read_select(field, raw)
        if value is None:
            options = " / ".join(field.options or [])
            return None, f"Tôi chưa rõ lựa chọn của bạn. {field.label} là: {options}?"
        return value, None

    if field.type == "number":
        value = _read_number(raw)
        if value is None:
            return None, f"{field.label} cần là một con số. Bạn cho tôi xin lại nhé?"
        return value, None

    if not raw:
        return None, f"Bạn cho tôi xin {field.label.lower()} nhé?"

    if field.pattern:
        tidied = _tidy_pattern_value(raw)
        if not re.match(field.pattern, tidied):
            return None, (
                f"{field.label} \"{raw}\" chưa đúng định dạng hệ thống nhận. "
                "Bạn kiểm tra lại giúp tôi nhé?"
            )
        return tidied, None

    return raw, None


# --- Chọn trường để hỏi --------------------------------------------------


def next_missing_field(
    schema: FormSchemaPayload, form_data: dict[str, str]
) -> FormFieldSchema | None:
    """Trường đầu tiên chưa có giá trị, theo đúng thứ tự khai trong schema.

    Thứ tự khai chính là thứ tự hỏi — người soạn schema quyết định mạch hội
    thoại, không phải code. Trường không bắt buộc vẫn được hỏi (cư dân có thể
    bỏ qua), vì `question` của chúng đã được soạn để hỏi.
    """
    for field in schema.fields:
        if field.key not in form_data:
            return field
    return None


def seed_from_message(schema: FormSchemaPayload, message: str) -> dict[str, str]:
    """Nhặt sẵn những trường cư dân đã khai ngay trong câu mở đầu.

    Cố ý **dè dặt**: chỉ nhận trường `select` (khớp với lựa chọn đóng) và
    trường có `pattern` (tự kiểm được). Trường chữ tự do thì không đoán — một
    câu như "Tôi muốn đăng ký thẻ xe" mà đem gán cả câu vào ô "Biển số xe" thì
    tệ hơn hẳn là hỏi thêm một lượt.
    """
    seeded: dict[str, str] = {}
    for field in schema.fields:
        if field.type == "select":
            value = _read_select(field, message)
            if value is not None:
                seeded[field.key] = value
        elif field.pattern:
            for token in re.findall(r"\S+", message):
                tidied = _tidy_pattern_value(token)
                if re.match(field.pattern, tidied):
                    seeded[field.key] = tidied
                    break
    return seeded


# --- Câu chữ gửi cho cư dân ---------------------------------------------


def build_question(field: FormFieldSchema, prefix: str = "") -> str:
    """Câu hỏi cho một trường — luôn lấy từ `field.question`, có gợi ý kèm.

    Gợi ý (danh sách lựa chọn, giá trị mặc định) ghép thêm ở đây chứ không
    viết cứng vào `question` trong seed: cùng một câu hỏi dùng lại được cho
    trường bắt buộc lẫn không bắt buộc.
    """
    parts = [field.question]
    if field.type == "select" and field.options:
        parts.append(f"({' / '.join(field.options)})")
    elif not field.required:
        hint = f"mặc định {field.default}" if field.default else "có thể bỏ qua"
        parts.append(f"(không bắt buộc — nhắn \"bỏ qua\" để {hint})")
    question = " ".join(parts)
    return f"{prefix}\n\n{question}" if prefix else question


def build_form_confirmation(
    schema: FormSchemaPayload, form_data: dict[str, str], task_name: str
) -> str:
    lines = [f"Đây là hồ sơ **{task_name}** tôi đã ghi lại giúp bạn:", ""]
    for field in schema.fields:
        value = form_data.get(field.key) or "—"
        lines.append(f"- **{field.label}**: {value}")
    required_docs = [a.label for a in schema.attachments if a.required]
    if required_docs:
        lines += ["", "Giấy tờ cần đính kèm khi gửi:"]
        lines += [f"- {label}" for label in required_docs]
    lines += [
        "",
        "Bạn xem lại giúp tôi. Đúng rồi thì bấm **Gửi hồ sơ**, cần sửa gì thì "
        "sửa thẳng trên form hoặc nhắn cho tôi.",
    ]
    return "\n".join(lines)


def build_disambiguation_message(options: list[ChecklistItem]) -> str:
    lines = ["Có mấy thủ tục cùng khớp. Bạn muốn làm cái nào?", ""]
    lines += [f"{i}. {item.task_name}" for i, item in enumerate(options[:4], 1)]
    return "\n".join(lines)


# --- Điều phối một lượt --------------------------------------------------


def _turn_for(
    schema: FormSchemaPayload,
    form_data: dict[str, str],
    item: ChecklistItem,
    prefix: str = "",
) -> FormTurn:
    """Hỏi trường còn thiếu kế tiếp, hoặc chốt lại hồ sơ nếu đã đủ."""
    field = next_missing_field(schema, form_data)
    if field is None:
        return FormTurn(
            answer=build_form_confirmation(schema, form_data, item.task_name),
            intent="form_review",
            checklist_item_id=item.checklist_item_id,
            form_schema=schema,
            form_data=form_data,
        )
    return FormTurn(
        answer=build_question(field, prefix),
        intent="form_generation",
        checklist_item_id=item.checklist_item_id,
        form_schema=schema,
        form_data=form_data,
    )


async def run_form_turn(
    db: Session,
    message: str,
    checklist_item_id: int | None,
    form_data: dict[str, str] | None,
) -> FormTurn | None:
    """Xử lý một lượt chat trong luồng điền hồ sơ.

    Trả `None` khi câu này **không thuộc luồng form** — gọi xong nhận None thì
    `/chat` đi tiếp xuống RAG y như trước. Đây là hợp đồng quan trọng nhất của
    module: mặc định là nhường, chỉ giữ lượt khi chắc chắn có thủ tục.
    """
    if checklist_item_id is not None:
        return _continue_form(db, message, checklist_item_id, form_data or {})
    return await _start_form(db, message)


async def _start_form(db: Session, message: str) -> FormTurn | None:
    """Lượt đầu — nhận ý định rồi mở luồng, hoặc nhường cho RAG."""
    match = await detect_procedure_intent(message, db)

    if match.item is not None:
        schema = store.get_form_schema(db, match.item.checklist_item_id)
        if schema is None:
            # Thủ tục có thật nhưng chưa soạn form (vd. "Ký nội quy toà nhà"):
            # để RAG trả lời bằng chữ, đừng mở một form rỗng.
            return None
        seeded = seed_from_message(schema, message)
        opening = f"Bạn muốn làm thủ tục **{match.item.task_name}**. Tôi hỏi bạn vài thông tin nhé."
        return _turn_for(schema, seeded, match.item, prefix=opening)

    if match.ambiguous and match.disambiguation_options:
        return FormTurn(
            answer=build_disambiguation_message(match.disambiguation_options),
            intent="disambiguation",
            options=match.disambiguation_options[:4],
        )

    return None


def _continue_form(
    db: Session, message: str, checklist_item_id: int, form_data: dict[str, str]
) -> FormTurn | None:
    """Lượt tiếp theo — đọc câu trả lời vào trường đang hỏi rồi hỏi trường sau."""
    item = db.get(ChecklistItem, checklist_item_id)
    schema = store.get_form_schema(db, checklist_item_id) if item else None
    if item is None or schema is None:
        return None

    form_data = dict(form_data)
    pending = next_missing_field(schema, form_data)
    if pending is None:
        # Đã đủ trường mà cư dân vẫn nhắn tiếp — dựng lại bản tóm tắt thay vì
        # im lặng, để họ biết đang chờ mình bấm Gửi.
        return _turn_for(schema, form_data, item)

    value, error = apply_answer(pending, message)
    if error is not None:
        # Hỏi lại đúng trường đó, kèm lý do. `form_data` giữ nguyên nên lượt
        # sau `next_missing_field` vẫn trả về chính trường này.
        return FormTurn(
            answer=build_question(pending, prefix=error),
            intent="form_generation",
            checklist_item_id=checklist_item_id,
            form_schema=schema,
            form_data=form_data,
        )

    form_data[pending.key] = value or ""
    return _turn_for(schema, form_data, item)
