# Handover — AI Form Generation: Phần AI

**Từ:** Claude (implementation)
**Cho:** Nguyễn Việt Hải — AI
**Ngày:** 2026-08-20
**Nguồn:** `docs/superpowers/specs/2026-08-20-ai-form-generation-design.md`
**Plan:** `docs/superpowers/plans/2026-08-20-ai-form-generation-plan.md`

---

## Tổng quan feature

Thay thế form cố định bằng **AI dẫn dắt cư dân** qua hội thoại để thu thập thông tin, sinh hồ sơ có cấu trúc, cư dân review và submit.

```
Cư dân bấm/trigger → AI hỏi → extract form_data → resident review → submit
```

---

## Phần của bạn (AI)

### 1. Đã làm sẵn

**`src/ai/intent.py`** — Task 3
- `detect_procedure_intent(message, db)` — 3 lớp: keyword exact → fuzzy → LLM fallback
- `_normalize()` — bỏ dấu tiếng Việt
- `_extract_keywords()` — tách từ 3+ ký tự, filter stopwords
- Trả về `ProcedureMatch(item, confidence, ambiguous, disambiguation_options)`
- ⚠️ Layer 3 LLM chưa wired — hiện tại chỉ trả về disambiguation options

**`src/ai/form_extraction.py`** — Task 7
- `extract_form_fields(schema, history)` — regex + heuristic, không LLM
- Extract select fields (normalized matching)
- Extract text/number fields
- Dùng default khi không extract được

**`POST /chat` integration** — Task 7
- Form generation chạy **TRƯỚC** RAG flow
- Trả về `intent="form_generation"` + `form_schema` + `form_data` + `checklist_item_id`
- Hoặc `intent="disambiguation"` khi ambiguous

### 2. Cần bạn làm (Phase 2)

#### 2a. Wire Layer 3 LLM vào `detect_procedure_intent`

```python
# src/ai/intent.py — Layer 3 hiện tại:
return ProcedureMatch(
    item=None, confidence="low",
    ambiguous=True,
    disambiguation_options=all_items[:4]
)
```

Cần: khi Layer 1+2 không match, gọi LLM để detect intent thay vì hỏi resident chọn.

#### 2b. Cải thiện `extract_form_fields`

Hiện tại dùng heuristic đơn giản. Cân nhắc:
- Dùng LLM để extract structured fields từ conversation history
- Hoặc cải thiện heuristic với better Vietnamese normalization

#### 2c. Prompt cho AI trong chat

AI cần biết:
1. Đang ở trong form generation mode
2. Hỏi theo `form_schema.fields[i].question`
3. Sau khi hỏi đủ → trả về form review

---

## Interface cần biết

### `detect_procedure_intent`

```python
from src.ai.intent import detect_procedure_intent
from sqlalchemy.orm import Session

match = detect_procedure_intent("Tôi muốn đăng ký thẻ xe máy", db_session)
# match.item — ChecklistItem hoặc None
# match.confidence — "high" | "medium" | "low"
# match.ambiguous — bool
# match.disambiguation_options — list[ChecklistItem]
```

### `extract_form_fields`

```python
from src.ai.form_extraction import extract_form_fields
from src.models.schemas import FormSchemaPayload

schema = FormSchemaPayload(...)  # từ DB
history = [
    {"role": "user", "content": "Ô tô"},
    {"role": "user", "content": "30A-123.45"},
]
data = extract_form_fields(schema, history)
# {"vehicle_type": "Ô tô", "plate": "30A-123.45"}
```

### `form_schema` trong DB

Mỗi procedure có `form_schema JSONB` trong `checklist_items`:

```sql
SELECT checklist_item_id, task_name, form_schema
FROM checklist_items
WHERE form_schema IS NOT NULL;
```

```json
{
  "fields": [
    {"key": "vehicle_type", "label": "Loại phương tiện",
     "type": "select", "options": ["Ô tô", "Xe máy"],
     "required": true, "question": "Bạn đăng ký thẻ xe gì?"},
    {"key": "plate", "label": "Biển số xe", "type": "text",
     "required": true, "question": "Biển số xe của bạn là gì?",
     "pattern": "^[0-9A-Z\\-]{5,15}$"}
  ],
  "attachments": [
    {"code": "cccd", "label": "Ảnh CCCD", "required": true},
    {"code": "dang_ky_xe", "label": "Ảnh đăng ký xe", "required": true}
  ]
}
```

### Các procedures đã có schema

| ID | Task | Fields |
|---|---|---|
| 38 | Làm thẻ cư dân (chủ hộ) | card_count |
| 39 | Làm thẻ cư dân (người thuê) | card_count |
| 42 | Đăng ký thẻ xe | vehicle_type, plate, quantity |
| 43 | Đăng ký chỗ đỗ xe cố định | vehicle_type, plate |
| 44 | Kích hoạt thẻ bể bơi | member_count |
| 45 | Kích hoạt thẻ phòng gym | member_count |
| 46 | Đăng ký thẻ thang máy | card_count |
| 47 | Đăng ký internet | provider, preferred_date |
| 48 | Đăng ký chuyển đồ vào căn hộ | move_date, time_slot, mover |
| 37 | Ký nội quy toà nhà | NULL (chỉ confirm) |

---

## Spec + Plan

- **Spec:** `docs/superpowers/specs/2026-08-20-ai-form-generation-design.md`
- **Plan:** `docs/superpowers/plans/2026-08-20-ai-form-generation-plan.md`

Đọc spec Section 5 (AI Pipeline) để hiểu luồng đầy đủ.

---

## Câu hỏi?

Liên hệ Hiếu (backend) nếu cần thay đổi API contracts.
