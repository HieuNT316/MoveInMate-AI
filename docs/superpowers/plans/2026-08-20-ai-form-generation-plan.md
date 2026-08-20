# AI Form Generation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI dẫn dắt cư dân qua hội thoại để thu thật thông tin, sinh hồ sơ có cấu trúc, resident review và submit. BQL nhận structured form_data.

**Architecture:** `form_schema` lưu trong cột `JSONB` trên bảng `checklist_items` (Supabase). Intent detection 3 lớp: keyword exact → fuzzy → LLM fallback. AI không ghi vào DB — chỉ trả `form_data` về FE. Resident submit trực tiếp lên `POST /applications` với `form_data`, checklist tự mark DONE khi resident bấm Gửi.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Supabase, Next.js, TypeScript

**Spec:** `docs/superpowers/specs/2026-08-20-ai-form-generation-design.md`

## Global Constraints

- `form_schema` lưu trong `checklist_items.form_schema JSONB` — không phải Chroma
- Checklist mark DONE khi resident submit, không chờ BQL approve
- Intent detection: keyword → fuzzy → LLM, thứ tự không đổi
- Backend validation 422 khi required field thiếu hoặc pattern sai
- Attachment phải upload TRƯỚC resident bấm Gửi
- Commit message: tiếng Việt có dấu, Co-Authored-By: Claude Opus 5

---

## File Map

### Backend — DB & Store

| File | Thay đổi |
|---|---|
| `alembic/versions/` | Migration thêm `form_schema` vào `checklist_items`, `form_data` vào `applications` |
| `src/models/db.py` | Thêm `FormField`, `FormSchema` Pydantic models; thêm `form_schema` column |
| `src/services/store.py` | `validate_form_data()`, `get_form_schema()`, update `create_application()` nhận `form_data` |

### Backend — Routes & AI

| File | Thay đổi |
|---|---|
| `src/api/routes.py` | `GET /checklist/{id}/form-schema`, update `POST /applications` nhận `form_data`, update `POST /chat` intent detection |
| `src/ai/intent.py` *(mới)* | `detect_procedure_intent()` — 3 lớp: keyword, fuzzy, LLM |
| `src/ai/form_extraction.py` *(mới)* | `extract_form_data()` — parse structured fields từ conversation |

### Seed & Scripts

| File | Thay đổi |
|---|---|
| `scripts/seed_form_schema.py` *(mới)* | Sinh `form_schema` cho 11 procedures từ `applicationForms.ts` hiện có |

### FE — API & Components

| File | Thay đổi |
|---|---|
| `web/lib/api.ts` | Thêm `FormSchema`, `FormField`, `ApplicationFormData` types; thêm `getFormSchema()`, `submitApplicationWithFormData()` |
| `web/app/components/FormReviewDialog.tsx` *(mới)* | Dialog resident review + edit form_data |
| `web/app/components/SubmitApplicationDialog.tsx` | Tích hợp AI form generation flow |
| `web/app/components/ChatSessionDialog.tsx` *(mới)* | Chat-driven trigger + disambiguation |

### Tests

| File | Thay đổi |
|---|---|
| `tests/test_intent_detection.py` *(mới)* | Unit tests cho keyword/fuzzy/LLM detection |
| `tests/test_form_extraction.py` *(mới)* | Unit tests cho extraction |
| `tests/test_routes.py` | Thêm tests cho `GET /checklist/{id}/form-schema`, `POST /applications` với `form_data` |

### Eval

| File | Thay đổi |
|---|---|
| `eval/questions.yaml` | Thêm FG01, FG02 |

---

## Task Definitions

---

### Task 1: DB migration — thêm cột `form_schema` và `form_data`

**Files:**
- Create: `alembic/versions/YYYYMMDDHHMMSS_add_form_schema_and_form_data.py`
- Modify: `src/models/db.py`

**Interfaces:**
- Consumes: nothing (pure migration)
- Produces: `checklist_items.form_schema JSONB`, `applications.form_data JSONB`

- [ ] **Step 1: Viết migration thêm 2 cột**

```python
# alembic/versions/YYYYMMDDHHMMSS_add_form_schema_and_form_data.py
from alembic import op

def upgrade():
    op.add_column("checklist_items", sa.Column("form_schema", JSONB, nullable=True))
    op.add_column("applications", sa.Column("form_data", JSONB, nullable=False, server_default="{}"))

def downgrade():
    op.drop_column("applications", "form_data")
    op.drop_column("checklist_items", "form_schema")
```

- [ ] **Step 2: Thêm Pydantic models cho form_schema**

```python
# src/models/schemas.py
class FormFieldSchema(BaseModel):
    key: str
    label: str
    type: Literal["text", "number", "select", "date"]
    options: list[str] | None = None
    required: bool = False
    question: str
    pattern: str | None = None
    default: str | None = None

class AttachmentSpecSchema(BaseModel):
    code: str
    label: str
    required: bool = False

class FormSchemaPayload(BaseModel):
    fields: list[FormFieldSchema]
    attachments: list[AttachmentSpecSchema] = []
```

- [ ] **Step 3: Chạy migration trên Postgres tạm**

Dùng docker Postgres tạm (xem cách Task 7 trong progress.md dùng):
```bash
docker run --name eval_pg -e POSTGRES_PASSWORD=test -d postgres
DATABASE_URL=postgresql://postgres:test@localhost:5432/test pytest alembic/versions/... -x
docker stop eval_pg && docker rm eval_pg
```

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/YYYYMMDDHHMMSS_add_form_schema_and_form_data.py src/models/schemas.py
git commit -m "feat(db): them form_schema va form_data JSONB columns
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Seed script — sinh form_schema cho 11 procedures

**Files:**
- Create: `scripts/seed_form_schema.py`
- Consumes: `web/lib/applicationForms.ts` (form field definitions hiện có)

**Interfaces:**
- Consumes: `web/lib/applicationForms.ts` — FORM_FIELDS map
- Produces: ghi `form_schema JSONB` vào bảng `checklist_items` trong Supabase

- [ ] **Step 1: Viết script sinh form_schema**

Script đọc `FORM_FIELDS` từ `web/lib/applicationForms.ts` bằng regex/string parsing (không import TypeScript). Với mỗi procedure:

1. Query `checklist_items` WHERE `task_name`
2. Sinh `FormSchemaPayload` từ field definitions
3. Update `form_schema = FormSchemaPayload.model_dump_json()`

```python
# scripts/seed_form_schema.py
"""Sinh form_schema JSONB cho checklist_items từ FORM_FIELDS hien co.

Chay: python -m scripts.seed_form_schema
"""
from src.database import SessionLocal
from src.models.schemas import FormSchemaPayload, FormFieldSchema, AttachmentSpecSchema

# Map task_name -> form_schema fields
# Doc tu web/lib/applicationForms.ts FORM_FIELDS

PROCEDURES = {
    "Đăng ký thẻ xe": FormSchemaPayload(fields=[
        FormFieldSchema(key="vehicle_type", label="Loại phương tiện",
                       type="select", options=["Ô tô","Xe máy"],
                       required=True, question="Bạn đăng ký thẻ xe gì?"),
        FormFieldSchema(key="plate", label="Biển số xe", type="text",
                       required=True, question="Biển số xe của bạn là gì?",
                       pattern=r"^[0-9A-Z\-]{5,15}$"),
        FormFieldSchema(key="quantity", label="Số lượng thẻ cần làm",
                       type="number", required=False, question="Bạn cần làm bao nhiêu thẻ?",
                       default="1"),
    ], attachments=[
        AttachmentSpecSchema(code="cccd", label="Ảnh CCCD chủ phương tiện", required=True),
        AttachmentSpecSchema(code="dang_ky_xe", label="Ảnh đăng ký xe hoặc hợp đồng", required=True),
        AttachmentSpecSchema(code="the_cu_dan", label="Ảnh thẻ cư dân", required=True),
    ]),
    # ... cac procedure khac
}

def main():
    db = SessionLocal()
    try:
        for task_name, schema in PROCEDURES.items():
            row = db.query(ChecklistItem).filter(
                ChecklistItem.task_name == task_name
            ).first()
            if row:
                row.form_schema = schema.model_dump()
                print(f"Updated: {task_name}")
            else:
                print(f"NOT FOUND: {task_name}")
        db.commit()
    finally:
        db.close()
```

- [ ] **Step 2: Chạy script**

```bash
python -m scripts.seed_form_schema
```

- [ ] **Step 3: Verify**

```python
# Kiem tra DB
db.query(ChecklistItem).filter(ChecklistItem.form_schema.isnot(None)).count()
# Phai tra ve 10 (ID 37 = NULL, khong co form)
```

- [ ] **Step 4: Commit**

```bash
git add scripts/seed_form_schema.py
git commit -m "feat(data): seed form_schema cho 11 procedures
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Intent detection — 3 lớp

**Files:**
- Create: `src/ai/intent.py`
- Modify: `src/ai/chat_llm.py` (để import get_llm)
- Test: `tests/test_intent_detection.py`

**Interfaces:**
- Consumes: `src/ai/chat_llm.get_llm()`, `src.models.db.ChecklistItem`
- Produces: `detect_procedure_intent(message: str, db: Session) -> ProcedureMatch`

```python
class ProcedureMatch(NamedTuple):
    item: ChecklistItem | None
    confidence: Literal["high", "medium", "low"]
    ambiguous: bool = False       # True = can hoi resident chon
    disambiguation_options: list[ChecklistItem] = []
```

- [ ] **Step 1: Viet test trước**

```python
# tests/test_intent_detection.py
def test_keyword_exact_match():
    from src.ai.intent import detect_procedure_intent
    from src.database import SessionLocal
    db = SessionLocal()
    # Procedure "Đăng ký thẻ xe" co form_schema
    match = detect_procedure_intent("Tôi muốn đăng ký thẻ xe máy", db)
    assert match.item.task_name == "Đăng ký thẻ xe"
    assert match.confidence == "high"
    assert not match.ambiguous

def test_ambiguous_requires_disambiguation():
    match = detect_procedure_intent("Tôi muốn làm thẻ", db)
    assert match.ambiguous
    assert len(match.disambiguation_options) > 1

def test_no_match_returns_none():
    match = detect_procedure_intent("Cho tôi xem thời tiết", db)
    assert match.item is None
    assert match.confidence == "low"
```

- [ ] **Step 2: Chạy test — verify FAIL**

```bash
pytest tests/test_intent_detection.py -v
# Expected: FAIL — module not found
```

- [ ] **Step 3: Implement intent detection**

```python
# src/ai/intent.py
from __future__ import annotations
import re
import unicodedata
from typing import Literal, NamedTuple

from sqlalchemy.orm import Session

from src.models.db import ChecklistItem

class ProcedureMatch(NamedTuple):
    item: ChecklistItem | None
    confidence: Literal["high", "medium", "low"]
    ambiguous: bool = False
    disambiguation_options: list[ChecklistItem] = []


def _normalize(text: str) -> str:
    """Bo dau, chuyen thanh lowercase."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(
        c for c in decomposed
        if unicodedata.category(c) != "Mn"
    ).replace("đ", "d")


def _extract_keywords(text: str) -> list[str]:
    """Tach tu khoa tu message."""
    words = re.findall(r"\b\w{3,}\b", text.lower())
    return [w for w in words if len(w) >= 3]


def detect_procedure_intent(message: str, db: Session) -> ProcedureMatch:
    norm = _normalize(message)
    keywords = _extract_keywords(message)

    # Lớp 1: Keyword exact match
    for kw in keywords:
        items = db.query(ChecklistItem).filter(
            ChecklistItem.task_name.ilike(f"%{kw}%")
        ).all()
        if len(items) == 1 and items[0].form_schema is not None:
            return ProcedureMatch(item=items[0], confidence="high")

    # Lớp 2: Fuzzy — kiem tra task_name co trong message
    all_items = db.query(ChecklistItem).filter(
        ChecklistItem.form_schema.isnot(None)
    ).all()
    candidates = [
        item for item in all_items
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

    # Lớp 3: LLM fallback — chi khi khong co match nao
    return ProcedureMatch(item=None, confidence="low", ambiguous=True,
                         disambiguation_options=all_items[:4])
```

- [ ] **Step 4: Chạy test — verify PASS**

```bash
pytest tests/test_intent_detection.py -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/ai/intent.py tests/test_intent_detection.py
git commit -m "feat(ai): intent detection 3 lop cho form generation
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Store + Validation — form_data trong create_application

**Files:**
- Modify: `src/services/store.py`
- Test: `tests/test_routes.py` (add tests for form_data validation)

**Interfaces:**
- Consumes: `src/models/schemas.FormSchemaPayload`, `src/ai/intent.ProcedureMatch`
- Produces: `store.validate_form_data(schema, form_data) -> list[str]`, `store.get_form_schema(db, item_id) -> FormSchemaPayload | None`

- [ ] **Step 1: Viet test cho validate_form_data**

```python
# tests/test_services/test_form_validation.py
from src.services.store import validate_form_data
from src.models.schemas import FormSchemaPayload, FormFieldSchema

schema = FormSchemaPayload(fields=[
    FormFieldSchema(key="plate", label="Biển số", type="text",
                   required=True, pattern=r"^[0-9A-Z\-]{5,15}$"),
    FormFieldSchema(key="quantity", label="Số thẻ", type="number",
                   required=False),
])

def test_validate_missing_required():
    errors = validate_form_data(schema, {})
    assert "Thiếu: Biển số" in errors

def test_validate_invalid_pattern():
    errors = validate_form_data(schema, {"plate": "abc"})
    assert any("sai định dạng" in e for e in errors)

def test_validate_ok():
    errors = validate_form_data(schema, {"plate": "30A-123.45", "quantity": "2"})
    assert errors == []
```

- [ ] **Step 2: Chạy test — verify FAIL**

```bash
pytest tests/test_services/test_form_validation.py -v
# Expected: FAIL — function not found
```

- [ ] **Step 3: Implement**

```python
# src/services/store.py

def validate_form_data(schema: FormSchemaPayload, form_data: dict) -> list[str]:
    errors = []
    for field in schema.fields:
        if field.required and field.key not in form_data:
            errors.append(f"Thiếu: {field.label}")
        elif field.key in form_data:
            value = form_data[field.key]
            if field.pattern and not re.match(field.pattern, str(value)):
                errors.append(f"{field.label} sai định dạng")
    return errors


def get_form_schema(db: Session, item_id: int) -> FormSchemaPayload | None:
    item = db.get(ChecklistItem, item_id)
    if item is None or item.form_schema is None:
        return None
    return FormSchemaPayload.model_validate(item.form_schema)


def create_application(
    db: Session,
    user_id: int,
    checklist_item_id: int,
    kind: str,
    note: str | None = None,
    form_data: dict | None = None,
) -> dict[str, Any]:
    # Validate form_data neu co
    if form_data:
        schema = get_form_schema(db, checklist_item_id)
        if schema:
            errors = validate_form_data(schema, form_data)
            if errors:
                raise ValidationError(errors)
    # ... giu nguyen logic cu, them form_data=form_data vao row
```

- [ ] **Step 4: Update POST /applications route**

```python
# src/api/routes.py
from pydantic import BaseModel

class ApplicationCreateV2(BaseModel):
    checklist_item_id: int
    note: str | None = None
    form_data: dict | None = None

@router.post("/applications", response_model=ApplicationResponse, status_code=201)
async def create_application_v2(
    body: ApplicationCreateV2,
    user: dict = Depends(require_resident),
    db: Session = Depends(get_db),
):
    try:
        return store.create_application(
            db,
            user["user_id"],
            body.checklist_item_id,
            kind=...,   # tu item.item_type
            note=body.note,
            form_data=body.form_data,
        )
    except store.ValidationError as e:
        raise HTTPException(422, {"detail": e.errors})
```

- [ ] **Step 5: Chạy test — verify PASS**

```bash
pytest tests/test_services/test_form_validation.py tests/test_routes.py -v
# Expected: PASS
```

- [ ] **Step 6: Commit**

```bash
git add src/services/store.py src/api/routes.py tests/
git commit -m "feat(store): validate form_data, create_application voi form_data
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: GET /checklist/{id}/form-schema endpoint + checklist timing

**Files:**
- Modify: `src/api/routes.py`
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: `store.get_form_schema()`
- Produces: `GET /checklist/{item_id}/form-schema`

- [ ] **Step 1: Viet test cho endpoint**

```python
# tests/test_routes.py
def test_get_form_schema_ok(client: TestClient, db_session):
    item = db_session.query(ChecklistItem).filter(
        ChecklistItem.form_schema.isnot(None)
    ).first()
    res = client.get(f"/checklist/{item.checklist_item_id}/form-schema",
                    headers=auth_header())
    assert res.status_code == 200
    assert "fields" in res.json()

def test_get_form_schema_null(client: TestClient, db_session):
    item = db_session.query(ChecklistItem).filter(
        ChecklistItem.form_schema.is_(None)
    ).first()
    res = client.get(f"/checklist/{item.checklist_item_id}/form-schema",
                    headers=auth_header())
    assert res.status_code == 404
```

- [ ] **Step 2: Implement endpoint**

```python
@router.get("/checklist/{item_id}/form-schema")
async def get_form_schema(
    item_id: int,
    user: dict = Depends(require_resident),
    db: Session = Depends(get_db),
):
    schema = store.get_form_schema(db, item_id)
    if schema is None:
        raise HTTPException(404, "Procedure does not have a form")
    return schema
```

- [ ] **Step 3: Checklist completion timing**

Spec quyết định: checklist mark DONE ngay khi resident submit.

```python
# Trong PATCH /checklist/{item_id} route, them:
@router.patch("/checklist/{item_id}")
async def patch_checklist_item(...):
    # ... existing logic ...
    if completed:
        # Chi update completion, khong thay doi status cua Application
        store.update_completion(db, item_id, user["user_id"], completed)
```

- [ ] **Step 4: Chạy test**

```bash
pytest tests/test_routes.py -k "form_schema or checklist" -v
```

- [ ] **Step 5: Commit**

```bash
git add src/api/routes.py tests/test_routes.py
git commit -m "feat(routes): GET /checklist/{id}/form-schema, checklist completion timing
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: FE — Form Review Dialog + API

**Files:**
- Create: `web/app/components/FormReviewDialog.tsx`
- Modify: `web/lib/api.ts`, `web/app/components/SubmitApplicationDialog.tsx`

**Interfaces:**
- Consumes: `api.getFormSchema()`, `api.submitApplicationWithFormData()`
- Produces: `FormReviewDialog` component

- [ ] **Step 1: Them types + API calls**

```typescript
// web/lib/api.ts
export type FormSchema = {
  fields: FormField[];
  attachments: AttachmentSpec[];
};

export type FormField = {
  key: string; label: string; type: "text"|"number"|"select"|"date";
  options?: string[]; required: boolean;
  question?: string; pattern?: string; default?: string;
};

export const getFormSchema = (itemId: number, token: string) =>
  authenticatedFetch(`/checklist/${itemId}/form-schema`, { token });

export const submitApplicationWithFormData = (
  userId: number,
  itemId: number,
  formData: Record<string, string>,
  token: string,
) =>
  authenticatedFetch("/applications", {
    method: "POST",
    token,
    body: { checklist_item_id: itemId, form_data: formData },
  });
```

- [ ] **Step 2: Viet FormReviewDialog**

```typescript
// web/app/components/FormReviewDialog.tsx
export default function FormReviewDialog({
  schema,               // FormSchema
  initialData,           // Record<string, string>
  itemName,              // "Đăng ký thẻ xe"
  onConfirm,              // (formData) => Promise<void>
  onBack,
}: {
  schema: FormSchema;
  initialData: Record<string, string>;
  itemName: string;
  onConfirm: (data: Record<string, string>) => Promise<void>;
  onBack: () => void;
}) {
  const [values, setValues] = useState(initialData);
  const [errors, setErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await onConfirm(values);
    } catch (e: any) {
      if (e?.status === 422) {
        setErrors(e.data?.detail ?? []);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open>
      <DialogContent>
        <h2>{itemName}</h2>
        {schema.fields.map(field => (
          <FormFieldInput
            key={field.key}
            field={field}
            value={values[field.key] ?? field.default ?? ""}
            onChange={v => setValues(v => ({...v, [field.key]: v}))}
            error={errors.find(e => e.includes(field.label))}
          />
        ))}
        {/* Attachment upload section */}
        <button onClick={handleSubmit} disabled={submitting}>
          {submitting ? "Đang gửi..." : "Gửi hồ sơ"}
        </button>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 3: Tích hợp vào SubmitApplicationDialog**

Trong `SubmitApplicationDialog.tsx` — sau khi AI fill form_data, thay vì chỉ gọi `api.createApplication`:
```typescript
// Sau khi AI thu thap du fields
if (schema) {
  setShowFormReview(true); // mo FormReviewDialog
} else {
  // Fallback: note-only (hiện tại)
  api.submitApplicationWithFormData(userId, item.checklist_item_id, {}, token);
}
```

- [ ] **Step 4: Test bằng tay**

1. Login với tài khoản demo
2. Vào checklist → bấm "Đăng ký thẻ xe"
3. Dialog hiện form với vehicle_type dropdown, plate text field
4. Sửa field → bấm Gửi
5. Kiểm tra `/admin/applications` thấy form_data

- [ ] **Step 5: Commit**

```bash
git add web/lib/api.ts web/app/components/FormReviewDialog.tsx \
         web/app/components/SubmitApplicationDialog.tsx
git commit -m "feat(web): FormReviewDialog va submitApplicationWithFormData
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: AI Pipeline — form generation trong chat

**Files:**
- Modify: `src/api/routes.py` (POST /chat logic), `src/ai/intent.py`
- Create: `src/ai/form_extraction.py`
- Test: `tests/test_form_extraction.py`

**Interfaces:**
- Consumes: `detect_procedure_intent()`, `get_form_schema()`
- Produces: `extract_form_fields()` — tra ve dict tu conversation history

- [ ] **Step 1: Viet test cho form extraction**

```python
# tests/test_form_extraction.py
from src.ai.form_extraction import extract_form_fields
from src.models.schemas import FormSchemaPayload, FormFieldSchema

schema = FormSchemaPayload(fields=[
    FormFieldSchema(key="vehicle_type", label="Loại phương tiện",
                   type="select", options=["Ô tô","Xe máy"], required=True),
    FormFieldSchema(key="plate", label="Biển số xe", type="text", required=True),
])

def test_extract_from_conversation():
    history = [
        {"role": "assistant", "content": "Bạn đăng ký thẻ xe gì?"},
        {"role": "user", "content": "Ô tô"},
        {"role": "assistant", "content": "Biển số xe của bạn là gì?"},
        {"role": "user", "content": "30A-123.45"},
    ]
    result = extract_form_fields(schema, history)
    assert result == {"vehicle_type": "Ô tô", "plate": "30A-123.45"}
```

- [ ] **Step 2: Implement extraction (regex + heuristic, không LLM để tránh cost)**

```python
# src/ai/form_extraction.py
def extract_form_fields(
    schema: FormSchemaPayload,
    history: list[dict],
) -> dict[str, str]:
    """Extract structured fields tu conversation history.

    Khong goi LLM — chi regex + heuristic tren history.
    Neu khong extract duoc -> tra ve {}
    """
    result = {}
    user_messages = [m["content"] for m in history if m["role"] == "user"]

    for field in schema.fields:
        for msg in reversed(user_messages):  # tu cuoi len
            if field.type == "select" and field.options:
                # Normalize va khop voi options
                for opt in field.options:
                    if normalize(msg) in normalize(opt) or normalize(opt) in normalize(msg):
                        result[field.key] = opt
                        break
            elif field.type in ("text", "number", "date"):
                # Lay toan bo cau
                result[field.key] = msg.strip()
                break
        if field.key not in result and field.default:
            result[field.key] = field.default

    return result
```

- [ ] **Step 3: Update POST /chat — integrate form generation**

Trong `POST /chat`, sau khi AI tra lời thường:

```python
# src/api/routes.py
from src.ai.intent import detect_procedure_intent
from src.ai.form_extraction import extract_form_fields

@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: dict = Depends(require_resident),
    db: Session = Depends(get_db),
):
    # 1. Intent detection (neu khong co checklist_item_id)
    match = None
    if not body.checklist_item_id:
        match = detect_procedure_intent(body.message, db)
        if match.item:
            schema = store.get_form_schema(db, match.item.id)
            if schema:
                # 2. Form generation
                extracted = extract_form_fields(schema, body.history or [])
                return {
                    "answer": build_form_confirmation(schema, extracted),
                    "intent": "form_generation",
                    "checklist_item_id": match.item.id,
                    "form_schema": schema,
                    "form_data": extracted,
                }
        elif match.ambiguous:
            return {
                "answer": build_disambiguation_message(match.disambiguation_options),
                "intent": "disambiguation",
            }
    # ... fallback RAG thường ...
```

- [ ] **Step 4: Chạy test**

```bash
pytest tests/test_form_extraction.py -v
pytest tests/test_routes.py -k chat -v
```

- [ ] **Step 5: Commit**

```bash
git add src/ai/form_extraction.py src/api/routes.py tests/
git commit -m "feat(ai): form generation trong chat, intent detection, extraction
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Eval questions + eval run

**Files:**
- Modify: `eval/questions.yaml`

**Interfaces:**
- Consumes: `eval/questions.yaml`
- Produces: eval run với FG01, FG02

- [ ] **Step 1: Thêm questions**

```yaml
  - id: FG01
    question: "Tôi muốn đăng ký thẻ xe máy biển 29P1-123.45"
    procedure: "Đăng ký thẻ xe"
    expect: form_generation
    expected_fields: { vehicle_type: "Xe máy", plate: "29P1-123.45" }
    dimension: intent_detection

  - id: FG02
    question: "Làm thẻ cư dân cho tôi"
    procedure: "Làm thẻ cư dân"
    expect: disambiguation
    dimension: ambiguity_handling
```

- [ ] **Step 2: Chạy eval**

```bash
python -m scripts.run_eval --api https://moveinmate-api-production.up.railway.app/api/v1 --limit 5
```

- [ ] **Step 3: Commit**

```bash
git add eval/questions.yaml
git commit -m "feat(eval): them FG01-FG02 cho form generation
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task Summary

| # | Task | Thứ tự | Dependent on |
|---|---|---|---|
| 1 | DB migration | 1 | — |
| 2 | Seed form_schema | 2 | Task 1 |
| 3 | Intent detection | 3 | — |
| 4 | Store + validate | 4 | Tasks 1, 2 |
| 5 | GET /checklist/{id}/form-schema | 5 | Tasks 1, 2, 4 |
| 6 | FE FormReviewDialog + API | 6 | Tasks 4, 5 |
| 7 | AI Pipeline (chat integration) | 7 | Tasks 3, 4, 5 |
| 8 | Eval questions | 8 | Tasks 7 |

**Thứ tự thực tế:** Tasks 1 và 3 song song (không đụng). Tasks 4, 5, 6, 7 cần 1+2+3 trước. Task 8 cuối cùng.
