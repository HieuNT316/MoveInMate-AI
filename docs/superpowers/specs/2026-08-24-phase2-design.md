# Phase 2 Design — MoveInMate

> **Trạng thái:** đang thiết kế
> **Ngày:** 24/08/2026
> **Team:** Hiếu (BE) · Hải (AI) · Thu (FE)

---

## 1. Tổng quan

Phase 2 bắt đầu 25/08/2026, hạn Demo Day 01/09/2026 (7 ngày thực tế). Mục tiêu: hoàn thiện 6 tính năng cốt lõi còn thiếu, bật LangSmith, quay video + làm pitch deck.

**Giả định US-11 (escalation):** khi RAG không tự tin trả lời, hệ thống tạo ticket cho BQL — cơ chế chưa có trong code hiện tại, sẽ implement từ đầu.

---

## 2. Tính năng

### 2.1 US-09 — FAQ cho BQL + nhánh fallback trong LangGraph

**Mục tiêu:** BQL quản lý FAQ trực tiếp; AI fallback sang FAQ trước RAG.

#### 2.1.1 Bảng mới: `faq`

```sql
CREATE TABLE faq (
    faq_id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_by INT REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON faq USING gin(to_tsvector('simple', question));
```

#### 2.1.2 API endpoints

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/admin/faq` | Danh sách FAQ, phân trang |
| POST | `/admin/faq` | Tạo FAQ mới |
| PATCH | `/admin/faq/{id}` | Sửa FAQ |
| DELETE | `/admin/faq/{id}` | Xoá FAQ |

Response shape: `{ faq_id, question, answer, created_at }`

#### 2.1.3 Nhánh fallback trong LangGraph

Thêm node `faq_lookup` **trước** `rag_retrieve`. Nếu `faq_lookup` tìm được câu trả lời → trả về FAQ; nếu không → xuống `rag_retrieve` như cũ.

```
rewrite_query → faq_lookup → rag_retrieve → generate
                  ↓ match          ↓ no match
              return FAQ        continue
```

**`faq_lookup` logic:**
1. Tìm kiếm full-text (to_tsvector) trên `question`
2. Dùng `question_similarity` (pg_trgm) để fuzzy match
3. Trả về FAQ nếu similarity > threshold (thử nghiệm: 0.3)
4. Không match → trả `None` → graph tiếp tục xuống RAG

**Priority:** FAQ → RAG. FAQ không match → RAG. Cả hai fail → `no_context`.

**Ranh giới:** FAQ là **câu hỏi-phản hồi đóng** — câu hỏi có câu trả lời cố định, không cần truy xuất tài liệu. RAG vẫn xử lý câu hỏi cần thông tin thủ tục.

#### 2.1.4 Phân công

| Ai | Việc |
|----|-------|
| Hiếu | Bảng `faq`, migration, 4 endpoints CRUD |
| Hải | Node `faq_lookup` + thêm vào graph |

**Effort:** ~10h (Hiếu 6h + Hải 4h)

---

### 2.2 US-11 — Cơ chế Escalation khi RAG không tự tin

**Mục tiêu:** cư dân hỏi câu ngoài phạm vi KB, hệ thống không im lặng mà tạo ticket để BQL xử lý.

#### 2.2.1 Bảng mới: `escalations`

```sql
CREATE TABLE escalations (
    escalation_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    conversation_id INT REFERENCES chat_conversations(conversation_id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,          -- câu trả lời AI đã gửi
    status ENUM('pending', 'resolved', 'dismissed') DEFAULT 'pending',
    resolved_by INT REFERENCES users(user_id),
    resolved_at TIMESTAMPTZ,
    bql_note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

#### 2.2.2 Trigger — khi nào tạo escalation

Trong `generate_node` (`src/agents/nodes/generate.py`), sau khi nhận `no_context=True`:

```python
if no_context:
    # Tạo escalation cho BQL
    await store.create_escalation(db, user_id, conversation_id, question, answer)
```

**Điều kiện trigger:** `no_context=True` **và** câu hỏi **thuộc phạm vi thủ tục nhà ở** (không phải chào hỏi, không phải hỏi thời tiết). Kiểm tra bằng intent classifier đơn giản: nếu có từ khoá thủ tục nhà ở trong câu → tạo escalation.

#### 2.2.3 Giao diện BQL xem escalation

Trang BQL mới `/bql/escalations` — danh sách escalation `pending`, kèm:
- Câu hỏi gốc của cư dân
- Câu trả lời AI đã gửi
- Hành động: "Đã xử lý" (đánh `resolved`) hoặc "Bỏ qua" (`dismissed`)

#### 2.2.4 Không gửi email/SMS

Escalation chỉ hiện trong trang BQL. Không thông báo đẩy.

#### 2.2.5 Phân công

| Ai | Việc |
|----|-------|
| Hiếu | Bảng `escalations`, migration, trigger trong `generate_node`, API BQL xem escalation |
| Thu | Trang `/bql/escalations` — danh sách + action |

**Effort:** ~14h (Hiếu 8h + Thu 6h)

---

### 2.3 US-12 — Dashboard BQL nâng cao

**Mục tiêu:** bổ sung biểu đồ và bộ lọc cho dashboard hiện tại.

#### 2.3.1 Biểu đồ

- **Biểu đồ tiến độ checklist** — bar chart: mỗi cư dân xem % hoàn thành (overall + bql_scope)
- **Biểu đồ trạng thái hồ sơ** — pie chart: tổng số hồ sơ theo status
- Thư viện: **Recharts** (đã có trong web/), đừng thêm thư viện mới

#### 2.3.2 Bộ lọc

- Lọc theo trạng thái checklist: "chưa bắt đầu", "đang làm", "đã xong"
- Lọc theo loại căn hộ
- Lọc theo ngày onboarding
- Tìm kiếm theo tên cư dân

#### 2.3.3 Phân công

| Ai | Việc |
|----|-------|
| Thu | Charts + filters + API endpoints cho dashboard nâng cao |

**Effort:** ~13h (Thu 13h, đã có dashboard mini 5h ở Phase 1)

---

### 2.4 US-14 — Nhắc việc còn thiếu (in-app)

**Mục tiêu:** cư dân thấy thông báo khi có thủ tục mới được thêm vào checklist của mình (ví dụ BQL thêm checklist item mới).

#### 2.4.1 Cơ chế

**Không polling, không WebSocket.** Giải pháp đơn giản: khi BQL tạo checklist item mới, backend ghi vào bảng `notifications`:

```sql
CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    type TEXT NOT NULL,        -- 'new_checklist_item'
    payload JSONB NOT NULL,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

FE poll endpoint `/notifications` mỗi 30 giây khi tab đang mở (chỉ poll khi logged in, không poll khi offline).

#### 2.4.2 API

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/notifications` | Danh sách notification của user, chưa đọc trước |
| PATCH | `/notifications/{id}/read` | Đánh dấu đã đọc |

#### 2.4.3 Phân công

| Ai | Việc |
|----|-------|
| Hiếu | Bảng, migration, endpoints |
| Thu | Toast notification trên FE, badge trên sidebar |

**Effort:** ~8h (Hiếu 5h + Thu 3h)

---

### 2.5 US-15 — Eval chất lượng LLM + Khảo sát người dùng

#### 2.5.1 Eval LLM (Hải)

Mở rộng `eval/questions.yaml` với ≥50 câu hỏi, đo trên production API. Chạy tự động trước mỗi lần push lên main.

Cải thiện eval script: đo riêng FAQ recall (nếu FAQ đã có) vs RAG recall.

#### 2.5.2 Khảo sát người dùng (song song)

**Thực tế:** không có người dùng thật trong thời gian demo. Khảo sát chạy **sau** Demo Day khi có cư dân thật.

**Trước Demo Day:** đo bằng **proxy metrics**:
- Số lượt cư dân dùng checklist
- Tỷ lệ cư dân hoàn thành ≥1 thủ tục trong checklist (từ `checklist_completions`)
- Thời gian trung bình từ onboarding → hoàn thành thủ tục đầu tiên

**Nút "Hữu ích không?" (nhắc phản hồi):** mỗi câu trả lời AI hiện nút "👍 hữu ích" / "👎 chưa hữu ích". Lưu vào bảng `chat_feedback`:

```sql
CREATE TABLE chat_feedback (
    feedback_id SERIAL PRIMARY KEY,
    chat_id INT REFERENCES chat_history(chat_id),
    is_helpful BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

#### 2.5.3 Phân công

| Ai | Việc |
|----|-------|
| Hải | Mở rộng eval (37→50+ câu), tự động hoá eval |
| Thu | Nút phản hồi + bảng `chat_feedback` + API |

**Effort:** ~9h (Hải 6h + Thu 3h)

---

### 2.6 US-16 — Form động nâng cao

**Mục tiêu:** mở rộng `form_schema` hiện tại hỗ trợ multi-step và conditional fields.

#### 2.6.1 Multi-step form

Thêm trường `step` trong `FormFieldSchema`:

```python
class FormFieldSchema(BaseModel):
    step: int = Field(default=1, ge=1)
    # step 1 = bước 1, step 2 = bước 2...
```

FE nhóm fields theo step, hiện navigation (Step 1/2/3). Backend vẫn nhận `form_data` flat — FE tự split.

#### 2.6.2 Conditional fields

Thêm trường `show_when` trong `FormFieldSchema`:

```python
class FormFieldSchema(BaseModel):
    show_when: dict | None = Field(
        default=None,
        description="Hiện field khi field khác có giá trị chỉ định. "
                    "VD: {\"key\": \"vehicle_type\", \"value\": \"Ô tô\"}"
    )
```

Backend lọc fields theo `show_when` trước khi trả về FE.

#### 2.6.3 Phân công

| Ai | Việc |
|----|-------|
| Hiếu | Schema + backend lọc conditional |
| Thu | Multi-step UI + conditional rendering |

**Effort:** ~8h (Hiếu 4h + Thu 4h)

---

### 2.7 LangSmith — Tracing

Bật bằng biến môi trường:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<key>
LANGCHAIN_PROJECT=moveinmate
```

Không cần sửa code. `src/agents/graph.py` dùng `langgraph` đã tự đẩy trace khi có biến.

**Phân công:** Hải — tạo tài khoản LangSmith + set biến trên Railway.

**Effort:** ~1h

---

### 2.8 Theo dõi chi phí token

**Mục tiêu:** ghi mỗi lượt gọi LLM + embed vào bảng để biết chi phí thực.

```sql
CREATE TABLE llm_usage_log (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    model TEXT NOT NULL,           -- 'gpt-4o-mini' / 'gemini-embedding-001'
    prompt_tokens INT,
    completion_tokens INT,
    cost_usd DECIMAL(8,6),
    endpoint TEXT NOT NULL,        -- 'chat' / 'embed'
    created_at TIMESTAMPTZ DEFAULT now()
);
```

Tính chi phí từ bảng giá OpenAI/Google. Ghi trong `src/services/llm.py` và `src/services/ingest.py`.

**Effort:** ~4h (Hiếu)

---

### 2.9 Video Demo + Pitch Deck

Song song với code. Không chờ code xong mới bắt đầu.

- **Video:** quay màn hình 3-5 phút, demo luồng cư dân (onboarding → checklist → chat → nộp hồ sơ) + luồng BQL (dashboard → duyệt hồ sơ)
- **Pitch Deck:** 10-15 slide, tập trung problem + solution + demo + tech

**Effort:** ~12h (team)

---

## 3. Phân công tổng

| Việc | Ai | Effort |
|-------|----|--------|
| US-09 FAQ (BE routes + migration) | Hiếu | 6h |
| US-09 FAQ (node + graph) | Hải | 4h |
| US-11 Escalation (BE + trigger) | Hiếu | 8h |
| US-11 Escalation (FE page) | Thu | 6h |
| US-12 Dashboard nâng cao | Thu | 13h |
| US-14 Notifications (BE) | Hiếu | 5h |
| US-14 Notifications (FE) | Thu | 3h |
| US-15 Eval mở rộng | Hải | 6h |
| US-15 Phản hồi (FE + DB) | Thu | 3h |
| US-16 Form nâng cao (BE) | Hiếu | 4h |
| US-16 Form nâng cao (FE) | Thu | 4h |
| LangSmith | Hải | 1h |
| Chi phí token | Hiếu | 4h |
| Video + Pitch Deck | Team | 12h |
| **Tổng** | | **~79h** |

**Capacity:** 3 người × 7 ngày = 21h/người = 63h. **Cần agent hỗ trợ** để bù ~16h.

---

## 4. Thứ tự ưu tiên

1. **LangSmith** — 1h, không phụ thuộc ai, bật trước để trace mọi thứ còn lại
2. **US-09 FAQ** — BE trước, AI sau; có thể song song
3. **US-11 Escalation** — có thể song song với US-09
4. **US-12 Dashboard** — Thu làm riêng
5. **US-16 Form nâng cao** — Thu + Hiếu, sau khi US-09/11 xong
6. **US-14 Notifications** — FE + BE, độc lập
7. **US-15 Eval + Phản hồi** — Hải + Thu
8. **Chi phí token** — Hiếu, độc lập
9. **Video + Pitch Deck** — bắt đầu ngày 28/08

---

## 5. Đã hoàn thành Phase 1 (không cần làm lại)

- Auth Supabase (JWT ES256 + JWKS)
- Checklist cá nhân hoá (rule engine, lọc trực tiếp)
- Chat RAG có trích nguồn (rewrite_query → rag → generate)
- Form động (form_schema JSONB, `GET /checklist/{id}/form-schema`)
- Nộp hồ sơ online (US-13 + US-10)
- Upload tài liệu BQL (US-08)
- Che PII trong chat_history
- Rate limiting
- Structured logging + exception handler
- `/health/deep`
- Railway Volume + Chroma seed

---

## 6. Out of scope

- Email/SMS notification
- OCR giấy tờ
- Đa ngôn ngữ
- Multi-khu
- Analytics nâng cao
