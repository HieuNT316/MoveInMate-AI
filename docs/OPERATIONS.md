# Vận hành: quan sát, guardrail, độ tin cậy

**Rà soát:** 11/08/2026 · đối chiếu hệ thống hiện tại với những gì một sản phẩm AI chạy thật cần có.

## Quan hệ với tài liệu khác

Phạm vi và quyết định nằm ở [`PROJECT_CHARTER.md`](./PROJECT_CHARTER.md); thiết kế kỹ thuật ở
[`architecture_diagram.md`](./architecture_diagram.md); phân công ở [`ROLES_AND_PLAN.md`](./ROLES_AND_PLAN.md).
Tài liệu này chỉ trả lời một câu hỏi: **nếu sản phẩm chạy thật, ta có biết nó đang hoạt động thế nào và có chặn được cái gì không.**

---

## 1. Hiện trạng

| Thành phần | Trạng thái | Bằng chứng |
|---|---|---|
| Guard chống bịa (`no_context`) | 🟡 có, **hỏng ở vùng biên** | Đo 11/08: chặn 4/4 câu ngoài lĩnh vực, **0/3** câu "đúng lĩnh vực nhưng KB không có" |
| Trích nguồn tất định | ✅ | `sources[]` sinh từ `rag_retrieve`, không hỏi LLM |
| Giới hạn độ dài đầu vào | ✅ | `ChatRequest.message` max 2000 ký tự |
| Trần token đầu ra | ✅ | `llm_max_tokens = 600` |
| Timeout gọi LLM | ✅ | `llm_timeout_seconds = 20` |
| Thử lại khi embed lỗi | ✅ | backoff trong `src/services/ingest.py` |
| Xác thực + phân quyền | ✅ | JWT Supabase, `require_admin` kiểm phía server |
| Đánh giá offline | ✅ | `eval/questions.yaml` 35 câu, `scripts/run_eval.py` |
| CI | ✅ | ruff + pytest |
| **Tracing (LangSmith)** | ❌ **khai nhưng chưa làm** | Có trong README, `requirements.txt`, sơ đồ kiến trúc — **`src/` không có dòng nào** |
| **Log có cấu trúc** | ❌ | Chỉ `print()` trong `main.py` và `ingest.py` |
| **Giới hạn tần suất** | ❌ | Không có. URL công khai + key OpenAI trả phí |
| **Health check thật** | ❌ | `/health` trả `ok` kể cả khi DB, Chroma hay LLM chết |
| **Theo dõi token / chi phí** | ❌ | Không ghi lại lượt gọi nào tốn bao nhiêu |
| **Guardrail đầu vào** | ❌ | Không lọc prompt injection, không che PII trước khi lưu `chat_history` |
| **Vòng phản hồi người dùng** | ❌ | Không có nút đánh giá câu trả lời |
| **Bắt lỗi tập trung** | ❌ | Không có exception handler; lỗi 500 biến mất không dấu vết |

---

## 2. Ba lỗ hổng cần xử lý trước

### 2.1 LangSmith — deliverable đang khai khống

`requirements.txt` ghi thẳng *"tracing — deliverable #4 của BTC"*, README liệt kê
`Observability | LangSmith`, sơ đồ kiến trúc vẽ hẳn một khối `LangSmith`. Nhưng
`grep -rn langsmith src/` không ra kết quả nào.

Đây không phải thiếu sót kỹ thuật đơn thuần — **tài liệu đang mô tả một thứ không tồn tại.**
Nếu mentor hỏi "cho xem trace" thì không có gì để mở.

Chi phí thật để làm: LangChain tự đẩy trace khi có biến môi trường, không cần sửa code:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<key>
LANGCHAIN_PROJECT=moveinmate
```

Ước tính **30 phút**, gồm cả tạo tài khoản và xác minh trace hiện ra.

### 2.2 Không có giới hạn tần suất trên URL công khai

`https://moveinmate-api-production.up.railway.app` mở cho cả internet, và mỗi
lượt `/chat` tốn một lần embedding (Google) cộng một lần gọi LLM (OpenAI, **key
trả phí của Hiếu**).

Không có gì ngăn một người gọi endpoint này vài nghìn lần. Rủi ro là tiền thật,
và hạn mức Google cạn thì cả nhóm mất luôn khả năng demo.

Mức đề xuất: **20 lượt/phút cho mỗi người dùng** với `/chat`, 100 lượt/phút cho
các endpoint đọc. Thư viện: `slowapi`.

### 2.3 Health check nông

```python
@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
```

Trả `ok` kể cả khi Postgres mất kết nối, Chroma hỏng index, hay hạn mức embedding
đã cạn. Railway dùng chính endpoint này để quyết định instance còn sống — nghĩa là
**một instance hỏng hoàn toàn vẫn được giữ trong vòng phục vụ**.

Đã có tiền lệ: ngày 11/08 index Chroma hỏng (`Error finding id`), `count()` vẫn
báo 386 và server vẫn khoẻ mạnh về mọi mặt quan sát được.

Cần tách hai đường: `/health` giữ nguyên cho Railway probe (nhanh, không phụ
thuộc bên ngoài), thêm `/health/deep` kiểm DB + Chroma + số chunk và trả 503 khi
có thành phần chết.

---

## 3. Còn lại, xếp theo mức nghiêm trọng

| Thành phần | Vì sao cần | Ưu tiên |
|---|---|---|
| **Log có cấu trúc** kèm `request_id` | `print()` không có mức, không có mốc thời gian, không lần được một request qua nhiều lớp. Lỗi trên Railway hiện là một dòng trần | W4 |
| **Theo dõi token/chi phí** mỗi lượt chat | Không biết một câu hỏi tốn bao nhiêu thì không đặt được ngân sách, cũng không phát hiện được lượt bất thường | W4 |
| **Bắt lỗi tập trung** | Lỗi 500 hiện không được ghi lại ở đâu ngoài log runtime của Railway | W4 |
| **Vòng phản hồi** (👍/👎 mỗi câu trả lời) | Nguồn dữ liệu duy nhất cho biết chất lượng thật ngoài 35 câu tự soạn. Cũng là đầu vào để mở rộng bộ eval | W4-W5 |
| **Che PII trước khi lưu `chat_history`** | Cư dân sẽ gõ số CCCD, số điện thoại vào ô chat. Hiện lưu nguyên văn vào Postgres | W4 |
| **Chống prompt injection** | Rủi ro thấp ở sản phẩm chỉ đọc như hiện tại, tăng lên khi agent có hành động ghi (Phase 2) | Phase 2 |

---

## 4. Ngưỡng cảnh báo đề xuất

Chưa có hệ thống cảnh báo; đây là mức để đặt khi dựng.

| Chỉ số | Ngưỡng | Ý nghĩa khi vượt |
|---|---|---|
| Tỷ lệ `no_context` | > 40% số lượt | KB thiếu nội dung, hoặc ngưỡng đặt quá chặt |
| Tỷ lệ `no_context` | < 5% số lượt | Guard hỏng — đang trả lời cả những câu không có căn cứ |
| p95 độ trễ `/chat` | > 8 giây | LLM hoặc embedding đang chậm |
| Lỗi 5xx | > 1% số request | Có thành phần hỏng |
| Chi phí LLM mỗi ngày | > ngưỡng đặt trước | Bị lạm dụng hoặc có vòng lặp |
| `collection.count()` | giảm so với lần trước | Index bị hỏng hoặc bị ghi đè |

Hai dòng đầu là một cặp: **chỉ nhìn một phía sẽ bỏ sót chế độ hỏng đối lập.** Guard
quá chặt và guard hỏng đều tệ, và cả hai đều không nhìn thấy được nếu chỉ đo tỷ lệ lỗi.

---

## 5. Cố ý không làm trong phạm vi project

- **Autoscale / multi-instance** — Chroma chạy trong tiến trình FastAPI, mỗi instance sẽ có một vector store riêng.
- **A/B testing prompt** — cần lưu lượng người dùng thật.
- **Đo mức độ hài lòng chính thức** — cần khảo sát người dùng thật, không có ở phạm vi này.
- **Cảnh báo qua email/SMS/Slack** — charter đã loại kênh thông báo ngoài app.
