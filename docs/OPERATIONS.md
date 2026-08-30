# Vận hành: quan sát, guardrail, độ tin cậy

**Rà soát:** 11/08/2026 · cập nhật 30/08/2026 sau khi dựng xong hệ thống quan sát.

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
| Tracing (LangSmith) | ✅ | `src/services/tracing.py` export cấu hình sang `os.environ` lúc khởi động |
| Log có cấu trúc | ✅ | `src/observability.py` — JSON mỗi dòng, kèm `request_id`, tự che chuỗi kết nối |
| Giới hạn tần suất | ✅ | `src/services/rate_limit.py` — cửa sổ cố định theo IP |
| Health check thật | ✅ | `/health/deep` kiểm DB + Chroma, trả 503 khi có thành phần chết |
| Theo dõi token / chi phí | ✅ | `src/services/cost_tracking.py` ghi vào `usage_logs` |
| Che PII trước khi lưu | ✅ | `src/services/pii.py`, gọi tại điểm ghi duy nhất `store.add_chat` |
| Bắt lỗi tập trung | ✅ | `unhandled_exception_handler` trong `main.py`, trả `request_id` để tra cứu |
| **Chỉ số + bảng điều khiển** | ✅ | `/api/v1/metrics` (Prometheus) · `docker-compose.yml` dựng sẵn Prometheus + Grafana |
| **Cảnh báo** | ✅ | `src/services/alerts.py` — webhook Slack, ngưỡng theo mục 4 dưới đây |
| **Vòng phản hồi người dùng** | ❌ | Vẫn chưa có nút 👍/👎 mỗi câu trả lời |
| **Chống prompt injection** | ❌ | Chưa lọc; rủi ro tăng khi agent có hành động ghi |
| **Bảo vệ endpoint `/metrics`** | ✅ | Bearer token (`METRICS_TOKEN`), sai/thiếu trả 404. Rỗng = mở, có cảnh báo lúc khởi động nếu `APP_ENV=production` |

**Rà lại 30/08.** Phần lớn khoảng trống nêu ngày 11/08 đã được lấp trong tuần
25-30/08. Hai mục còn ❌ ở trên là những gì thực sự chưa làm.

---

## 2. Ba lỗ hổng ưu tiên (nêu 11/08) — đã xử lý xong

| Lỗ hổng | Đã làm gì | Ngày |
|---|---|---|
| **LangSmith khai khống** — README và sơ đồ kiến trúc vẽ khối LangSmith nhưng `grep -rn langsmith src/` không ra gì | `src/services/tracing.py` export cấu hình sang `os.environ` lúc khởi động; tắt mặc định để prompt của cư dân không vô tình bị gửi ra dịch vụ ngoài | 25/08 |
| **Không có giới hạn tần suất** trên URL công khai — mỗi lượt `/chat` tốn tiền thật | `src/services/rate_limit.py`: 10 lượt/phút và 100 lượt/giờ cho `/chat`, 20/phút cho tải tệp. Tự viết, không thêm phụ thuộc — dịch vụ chạy một instance | 25/08 |
| **Health check nông** — `/health` trả `ok` kể cả khi Chroma hỏng | Thêm `/health/deep` kiểm DB + Chroma, trả 503 khi có thành phần chết. `count() == 0` tính là hỏng, không phải trạng thái hợp lệ | 25/08 |

---

## 3. Còn lại, xếp theo mức nghiêm trọng

| Thành phần | Vì sao cần | Trạng thái |
|---|---|---|
| **Vòng phản hồi** (👍/👎 mỗi câu trả lời) | Nguồn dữ liệu duy nhất cho biết chất lượng thật ngoài 37 câu tự soạn. Cũng là đầu vào để mở rộng bộ eval | Chưa làm |
| **Chống prompt injection** | Rủi ro thấp khi sản phẩm chỉ đọc, tăng lên khi agent có hành động ghi | Chưa làm |
| **Đưa `alerts` vào cùng nguồn với `usage_logs`** | `AlertService` đếm chi phí trong bộ nhớ tiến trình, khởi động lại là mất; `usage_logs` mới là bản ghi bền | Cân nhắc Phase 3 |

**Các mục của bảng cũ** (log có cấu trúc, theo dõi chi phí, bắt lỗi tập trung,
che PII, bảo vệ `/metrics`) đã làm xong trong tuần 25-30/08 — xem bảng hiện
trạng mục 1.

Riêng `METRICS_TOKEN` **chưa đặt trên Railway** — cơ chế đã có, còn thiếu bước
cấu hình. Backend sẽ ghi cảnh báo `metrics_endpoint_unprotected` mỗi lần khởi
động cho tới khi đặt.

---

## 4. Ngưỡng cảnh báo đề xuất

Bốn ngưỡng đầu **đã cài** trong `src/services/alerts.py`, bắn webhook Slack,
cách nhau tối thiểu 5 phút để không dội tin. Hai ngưỡng cuối chưa cài.

| Chỉ số | Ngưỡng | Ý nghĩa khi vượt | Đã cài |
|---|---|---|---|
| Lỗi 5xx | > 1% số request (cửa sổ 5 phút, tối thiểu 10 mẫu) | Có thành phần hỏng | ✅ |
| p95 độ trễ | > 8 giây | LLM hoặc embedding đang chậm | ✅ |
| Chi phí LLM mỗi ngày | > `ALERT_COST_DAILY_THRESHOLD` (mặc định $10) | Bị lạm dụng hoặc có vòng lặp | ✅ |
| Health check hỏng | 3 lần liên tiếp | DB hoặc Chroma chết | ✅ |
| Tỷ lệ `no_context` | > 40% số lượt | KB thiếu nội dung, hoặc ngưỡng đặt quá chặt | ❌ có chỉ số, chưa cảnh báo |
| Tỷ lệ `no_context` | < 5% số lượt | Guard hỏng — đang trả lời cả những câu không có căn cứ | ❌ |
| `collection.count()` | giảm so với lần trước | Index bị hỏng hoặc bị ghi đè | ❌ |

Hai dòng `no_context` là một cặp: **chỉ nhìn một phía sẽ bỏ sót chế độ hỏng đối
lập.** Guard quá chặt và guard hỏng đều tệ, và cả hai đều không nhìn thấy được
nếu chỉ đo tỷ lệ lỗi. `moveinmate_no_context_ratio` đã có trên bảng điều khiển
nhưng chưa gắn ngưỡng cảnh báo — đó là việc còn nợ.

---

## 5. Cố ý không làm trong phạm vi project

- **Autoscale / multi-instance** — Chroma chạy trong tiến trình FastAPI, mỗi instance sẽ có một vector store riêng.
- **A/B testing prompt** — cần lưu lượng người dùng thật.
- **Đo mức độ hài lòng chính thức** — cần khảo sát người dùng thật, không có ở phạm vi này.
- **Thông báo cho CƯ DÂN qua email/SMS** — charter đã loại kênh ngoài app.
  (Cảnh báo Slack ở mục 4 là chuyện khác: gửi cho ĐỘI VẬN HÀNH, không phải người dùng.)
