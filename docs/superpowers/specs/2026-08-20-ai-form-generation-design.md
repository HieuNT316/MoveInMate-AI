# Spec: AI-led Form Generation — Chat → Structured Application

> **Trạng thái:** Draft v2 (sửa Critical C1-C3, Important I1-I4)
> **Ngày:** 2026-08-20
> **Author:** Claude Opus 5

## 1. Mục tiêu

Thay thế form cố định bằng **AI dẫn dắt cư dân** qua hội thoại để thu thập thông tin, sinh hồ sơ có cấu trúc, rồi cư dân review và gửi. BQL nhận hồ sơ đã verify — không phải bản thô từ AI.

**Tư duy sản phẩm:** Nếu cư dân vẫn phải tự điền form — app không tiện hơn giấy. AI phải **hỏi** và cư dân chỉ **kiểm tra và sửa**. Không ai phải hiểu "form nào cần gì".

## 2. Kiến trúc tổng quan

```
┌──────────────────────────────────────────────────────────────┐
│  RESIDENT                                                  │
│                                                             │
│  [Checklist]  ──bấm HOẶC chat──→  [AI Chat Session]     │
│        │                                    │                │
│        │                          Keyword match              │
│        │                         ↓                           │
│        │                  DB → form_schema                  │
│        │                         ↓                           │
│        │                  AI hỏi cư dân                    │
│        │                         ↓                           │
│        │                  Extract structured fields            │
│        │                         ↓                           │
│        │              [Form Review UI]                       │
│        │             Cư dân sửa + confirm                   │
│        │                         ↓                           │
│        │              POST /applications                    │
│        │              + attachments                         │
│        │                         ↓                           │
│        │         PATCH /checklist/{id} → DONE              │
└──────────────────────────────────────────────────────────────┘
```

**Điểm khác với Draft v1:** `form_schema` lưu trong **Supabase DB** (cột `form_schema` trên bảng `checklist_items`), không phải Chroma. Intent detection dùng **keyword matching → fuzzy → LLM fallback**.

## 3. Trigger — hai entry point

### 3a. Checklist-driven (bấm)

Cư dân bấm vào checklist item (`item_type = "bql_actionable"` hoặc `"third_party_info"`).

- Context: `{ checklist_item_id, task_name, item_type, form_schema }`
- Context **luôn có sẵn** `form_schema` — không cần tra KB, không cần intent detection

### 3b. Chat-driven (nói)

Cư dân chat: *"Tôi muốn đăng ký thẻ xe."*

**Cơ chế intent detection — 3 lớp (ưu tiên giảm dần):**

```
Lớp 1 — Keyword exact match (thực hiện trước):
  Tách từ khóa từ message
  Query checklist_items WHERE task_name LIKE '%keyword%'
  Nếu khớp đúng 1 → proceed

Lớp 2 — Fuzzy match (thực hiện khi Lớp 1 không khớp):
  Từ khóa rút gọn: "thẻ xe" → "Đăng ký thẻ xe"
  Wildcard: WHERE task_name ILIKE '%the_xe%'
  Nếu khớp đúng 1 → proceed

Lớp 3 — LLM fallback (thực hiện khi Lớp 1+2 ambiguous):
  Gọi LLM: "Câu 'Tôi muốn đăng ký thẻ xe máy' có intent khớp với
            ['Làm thẻ cư dân (chủ hộ)', 'Đăng ký thẻ xe', 'Kích hoạt thẻ bể bơi'] không?
            Trả: Tên đúng hoặc 'khong_khop'"
  Nếu khớp → proceed
  Nếu ambiguous → hỏi xác nhận: "Bạn muốn đăng ký thẻ xe đúng không?"

Nếu không khớp gì → fallback sang RAG thường (hiện tại)
```

**Disambiguation flow khi ambiguous:**
```
AI: "Bạn muốn làm thẻ gì?"
Resident: "thẻ"
AI: "Có nhiều loại thẻ. Bạn muốn:
  1. Thẻ cư dân
  2. Thẻ xe
  3. Thẻ thang máy
  4. Thẻ bể bơi / gym
Bấm số để chọn."
```

Hai entry point cùng vào downstream: keyword/fuzzy/LLM match → `form_schema` → AI hỏi → extract → review → submit.

## 4. form_schema — lưu trong Supabase DB

### 4.1 Vì sao không phải Chroma/KB frontmatter

**Draft v1 sai:** Chroma chỉ lưu text content đã chunk. Frontmatter YAML không được embed — không retrieve được. KB frontmatter là metadata để đọc bằng mắt, không phải để query.

**Draft v2:** `form_schema` lưu trong cột `form_schema JSONB` trên bảng `checklist_items`. Mỗi procedure có đúng 1 `form_schema`, đọc bằng `checklist_item_id`.

### 4.2 Cấu trúc trong DB

```sql
-- Migration
ALTER TABLE checklist_items ADD COLUMN form_schema JSONB DEFAULT NULL;

-- Ví dụ row
checklist_item_id | task_name              | form_schema
-----------------|------------------------|----------------------------
37               | Ký nội quy toà nhà  | NULL  (chỉ confirm, không form)
42               | Đăng ký thẻ xe     | {fields: [...], attachments: [...]}
```

**Migrate existing data:** Viết script sinh `form_schema` cho 11 items từ `applicationForms.ts` hiện có, insert vào DB. Không thay đổi file `.md`.

### 4.3 Schema tổng quát

```typescript
type FormField = {
  key: string;
  label: string;
  type: "text" | "number" | "select" | "date";
  options?: string[];         // cho type=select
  required: boolean;
  question: string;           // câu hỏi AI dùng để hỏi cư dân
  pattern?: string;             // regex validation (optional)
  default?: string;             // giá trị mặc định
};

type AttachmentSpec = {
  code: string;               // khớp required_documents.code
  label: string;
  required: boolean;
};

type FormSchema = {
  fields: FormField[];
  attachments: AttachmentSpec[];
};
```

### 4.4 Các thủ tục cần sinh schema

| ID | Task | form_schema fields |
|---|---|---|
| 37 | Ký nội quy toà nhà | `NULL` (chỉ confirm, upload ảnh) |
| 38 | Làm thẻ cư dân (chủ hộ) | `card_count` |
| 39 | Làm thẻ cư dân (người thuê) | `card_count` |
| 42 | Đăng ký thẻ xe | `vehicle_type`, `plate`, `quantity` |
| 43 | Đăng ký chỗ đỗ xe cố định | `vehicle_type`, `plate` |
| 44 | Kích hoạt thẻ bể bơi | `member_count` |
| 45 | Kích hoạt thẻ phòng gym | `member_count` |
| 46 | Đăng ký thẻ thang máy | `card_count` |
| 47 | Đăng ký internet | `provider`, `preferred_date` |
| 48 | Đăng ký chuyển đồ vào căn hộ | `move_date`, `time_slot`, `mover` |

## 5. AI Pipeline

### 5.1 Lấy form_schema

```
Checklist-driven:  form_schema có sẵn trong checklist item context
Chat-driven:       keyword match → query DB WHERE task_name ILIKE '%...%'
                    → trả về form_schema + checklist_item_id
                    → Nếu NULL form_schema → note-only flow (hiện tại)
```

### 5.2 Chat flow

```
AI:
  [Xác nhận intent]
  "Bạn muốn đăng ký thẻ xe. Đúng không?"

Resident:
  "Đúng rồi"

AI:
  [Đọc form_schema.fields theo thứ tự, hỏi từng required field trước]
  "Loại phương tiện: Ô tô hay xe máy?"

Resident:
  "Ô tô"

AI:
  [Fill field, hỏi tiếp]
  "Biển số xe của bạn là gì? (định dạng: 30A-123.45)"

Resident:
  "30A-123.45"

AI:
  [Validate pattern]
  Nếu OK: "Bạn cần làm bao nhiêu thẻ? (mặc định: 1)"

Resident:
  "1"

AI:
  [Tất cả required fields đã đủ]
  [Hiển thị form review]
  "Đây là hồ sơ của bạn:

  Loại phương tiện: Ô tô
  Biển số: 30A-123.45
  Số thẻ: 1

  Đúng không? Bạn có thể sửa trực tiếp trên form hoặc nhắn tôi để cập nhật."
```

### 5.3 Extraction & Validation

- AI extract key-value từ conversation vào structured dict `{vehicle_type: "Ô tô", plate: "30A-123.45", quantity: "1"}`
- **AI KHÔNG ghi vào DB** — chỉ trả về `form_data` cho FE
- FE gửi trực tiếp lên `POST /applications` với `form_data`
- Backend validate required fields + pattern
- Nếu backend trả 422 → FE highlight field còn thiếu/sai

### 5.4 Disambiguation

Khi keyword/fuzzy khớp nhiều hơn 1 procedure hoặc resident trả lời mơ hồ:

```
AI: "Có nhiều loại thẻ. Bạn muốn:
  1. Thẻ cư dân
  2. Thẻ xe máy / ô tô
  3. Thẻ bể bơi / gym
  4. Thẻ thang máy
Bấm số để chọn."
```

FE render inline buttons cho 4 lựa chọn. Resident bấm → AI proceed với procedure đã chọn.

## 6. Backend — thay đổi

### 6.1 Bảng `applications` + `checklist_items`

```sql
ALTER TABLE applications ADD COLUMN form_data JSONB DEFAULT '{}';

-- form_schema lưu trong bảng checklist_items đã có
ALTER TABLE checklist_items ADD COLUMN form_schema JSONB DEFAULT NULL;
```

### 6.2 API endpoints mới

```
GET  /checklist
  → trả kèm form_schema cho mỗi item

GET  /checklist/{item_id}/form-schema
  → trả FormSchema cho item đó (404 nếu NULL)

GET  /chat
  body: { message, history?, checklist_item_id? }
  Nếu checklist_item_id có → dùng form_schema trực tiếp
  Nếu checklist_item_id null → intent detection 3 lớp
  Trả: { answer, intent, checklist_item_id?, form_schema?, form_data? }

POST /applications
  payload:
    {
      checklist_item_id: int,
      note?: string,          -- vẫn giữ, cho fallback
      form_data?: dict        -- structured fields
    }
  validate: required fields phải có, pattern phải khớp
  Trả 422: { missing_fields: [...], invalid_fields: [...] }
  Lưu: form_data vào cột mới

GET  /applications/{id}
GET  /admin/residents/{id}/applications
  → trả kèm form_data

PATCH /admin/applications/{id}
  body: { status, bql_note?, form_data? }
  BQL sửa form_data nếu resident nhập sai
```

### 6.3 Intent detection (chat trigger)

```python
def detect_procedure_intent(message: str, db: Session) -> ProcedureMatch:
    """3 lớp: keyword → fuzzy → LLM."""
    # Lớp 1: keyword exact
    keywords = extract_keywords(message)
    for kw in keywords:
        items = db.query(ChecklistItem).filter(
            ChecklistItem.task_name.ilike(f"%{kw}%")
        ).all()
        if len(items) == 1:
            return ProcedureMatch(item=items[0], confidence="high")

    # Lớp 2: fuzzy (từ rút gọn)
    normalized = normalize_vietnamese(message)
    for item in db.query(ChecklistItem).all():
        if normalize_vietnamese(item.task_name) in normalized:
            return ProcedureMatch(item=item, confidence="medium")

    # Lớp 3: LLM fallback → hỏi resident chọn
    return ProcedureMatch(item=None, confidence="low", ambiguous=True)
```

### 6.4 Checklist completion timing

**Điều quan trọng được quyết định tại đây:**

```
Luồng: resident bấm Gửi
  1. POST /applications (form_data)         ← validation
  2. PATCH /checklist/{item_id} (done)    ← mark COMPLETED

→ Checklist marked DONE ngay khi resident submit
  BQL approve/reject là internal workflow, không block resident's progress
```

**Tại sao:** Đây là online submission. Resident đã nộp đầy đủ thông tin và giấy tờ → họ đã hoàn thành nghĩa vụ. BQL duyệt là quy trình nội bộ, không nên treo resident's checklist.

## 7. FE — Resident Review UI

### 7.1 Form Review Dialog

```
┌──────────────────────────────────────────────┐
│  Đăng ký thẻ xe                             │
├──────────────────────────────────────────────┤
│  Loại phương tiện                            │
│  [Ô tô                          ▼]          │
│                                              │
│  Biển số xe                                  │
│  [30A-123.45                         ]        │
│  ↑ required — highlight đỏ nếu backend báo sai│
│                                              │
│  Số lượng thẻ cần làm                        │
│  [1                                    ]    │
│                                              │
│  ── Giấy tờ cần upload ──                    │
│  ☑ Ảnh CCCD chủ phương tiện      [Tải lên] │
│  ☑ Ảnh đăng ký xe hoặc hợp đồng   [Tải lên] │
│  ☑ Ảnh thẻ cư dân                  [Tải lên] │
│                                              │
│  [Quay lại]              [Gửi hồ sơ]        │
└──────────────────────────────────────────────┘
```

- Resident sửa trực tiếp trên form (inline edit)
- AI không cần re-call — `form_data` đã có structured values
- Backend 422 → FE highlight field lỗi với message cụ thể
- Sau khi submit thành công → checklist item tự đánh dấu DONE

### 7.2 Attachment upload timing

**Attachments phải được upload TRƯỚC khi resident bấm Gửi.**

```
Dialog state machine:
  [1. AI hỏi → form_data đầy]
      ↓
  [2. Resident sửa form → AI cập nhật form_data]
      ↓
  [3. Attachment upload — resident upload ĐỦ required docs]
      ↓
  [4. Bấm Gửi → POST /applications + PATCH checklist DONE]
```

Nếu resident bấm Gửi mà thiếu attachment → trả lỗi tương tự 422, highlight attachment còn thiếu.

## 8. BQL Admin

### 8.1 Xem hồ sơ

`GET /admin/residents/{id}/applications` trả kèm `form_data`. BQL thấy structured fields, không cần đọc `note`.

### 8.2 Duyệt hồ sơ

`PATCH /admin/applications/{id}` với `{ status, bql_note, form_data }`. BQL sửa `form_data` nếu resident nhập sai.

## 9. Deployment

### Phase 1 (trước 24/08)
- Thêm cột `form_schema JSONB` vào `checklist_items`
- Thêm cột `form_data JSONB` vào `applications`
- Sinh form_schema cho 11 procedures từ `applicationForms.ts` hiện có
- Intent detection 3 lớp
- AI pipeline: match → hỏi → extract → review → submit
- Resident review dialog
- **Checklist-driven trigger chỉ** (chat-driven → Phase 2)

### Phase 2 (sau 24/08)
- Chat-driven trigger
- Resident review dialog inline trong chat
- AI suggest procedure dựa trên conversation context

## 10. Evaluation

### 10.1 Metrics

- **Form completion rate**: % resident bấm Gửi sau khi AI hỏi xong
- **Edit rate**: % resident sửa ≥1 field → đo AI accuracy
- **Disambiguation rate**: % conversation cần hỏi xác nhận
- **422 error rate**: % resident submit bị reject do validate fail

### 10.2 Eval questions bổ sung

```yaml
- id: FG01
  question: "Tôi muốn đăng ký thẻ xe máy biển 29P1-123.45"
  expect: form_generation
  procedure: "Đăng ký thẻ xe"
  expected_fields: { vehicle_type: "Xe máy", plate: "29P1-123.45" }

- id: FG02
  question: "Làm thẻ cư dân cho tôi"
  expect: disambiguation
  # → AI phải hỏi: chủ hộ hay người thuê?
```

## 11. Rủi ro và giảm nhẹ

| Rủi ro | Giảm nhẹ |
|---|---|
| AI hỏi thiếu required field | Backend 422 → FE highlight field |
| Resident nhập plate sai format | Pattern regex trong dialog + AI validate |
| Intent detection nhầm procedure | 3 lớp (keyword → fuzzy → LLM) + disambiguation |
| Resident upload thiếu attachment | Frontend disable nút Gửi + backend 422 |
| `form_schema` NULL cho procedure mới | Script sinh schema check mọi `bql_actionable` items có schema |
| Schema thay đổi giữa conversation | Conversation snapshot form_schema tại thời điểm bắt đầu |
