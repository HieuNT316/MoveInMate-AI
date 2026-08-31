# Bàn giao cho Hải — 2 lỗi trong `src/agents/`

**Từ:** Hiếu (BE) · **Ngày:** 31/08/2026
**Phát hiện qua:** review toàn bộ backend trước Demo Day

Hai lỗi dưới đây nằm trong `src/agents/` nên thuộc vai AI, tôi không tự sửa.
Cả hai **đã kiểm chứng bằng cách chạy thật**, không phải suy đoán.

---

## 1. Theo dõi chi phí LLM chết im lặng — `usage_logs` không có dòng nào từ chat

**Chỗ sai:** `src/agents/nodes/generate.py:184`, `:213` và
`src/agents/nodes/rewrite_query.py:70`

```python
usage = getattr(response, "usage", None)
```

`AIMessage` của LangChain **không có** thuộc tính `usage`. Nó tên là
`usage_metadata`. Đã đo:

```
co thuoc tinh .usage          ? False
co thuoc tinh .usage_metadata ? True -> {'input_tokens': 10, 'output_tokens': 5, ...}
```

`getattr(..., None)` nuốt gọn nên không có lỗi nào lộ ra.

**Hậu quả dây chuyền:**

| Thứ | Trạng thái |
|---|---|
| `input_tokens` / `output_tokens` | luôn `None` |
| `_log_chat_usage` (`routes.py`) | luôn bỏ qua, không ghi gì |
| `usage_logs` | rỗng (kiểm trên Postgres thật: chỉ 1 dòng, từ test tôi chạy tay) |
| `moveinmate_cost_today_usd` | luôn `0` |
| `GET /admin/usage/summary` | rỗng |
| Cảnh báo vượt chi phí $10/ngày | **không bao giờ bắn** |

Cái cuối đáng lo nhất: ngưỡng chi phí là thứ duy nhất phát hiện bị lạm dụng
hoặc có vòng lặp gọi LLM, mà nó đang tê liệt.

**Sửa:** đổi `getattr(response, "usage", None)` thành
`getattr(response, "usage_metadata", None)`, rồi đọc `input_tokens` /
`output_tokens` từ dict đó (`usage_metadata` là dict, không phải object có
thuộc tính — kiểm lại chỗ đọc phía sau).

**Cần thêm một test bắt được lỗi này.** `tests/test_cost_tracking.py` hiện chỉ
gọi thẳng `log_usage()`, không đi qua mối nối `generate` → `routes`, nên 610
test vẫn xanh suốt thời gian tính năng này chết.

---

## 2. Lỗi gọi LLM biến mất hoàn toàn khỏi log

**Chỗ sai:** `src/agents/nodes/generate.py:187-192`, `:216-222`,
`src/agents/nodes/rewrite_query.py:73-77` — ba khối `except Exception` không
log gì cả.

Nếu OpenAI hết quota hoặc timeout **giữa buổi demo**, cư dân nhận
`GENERATION_FAILED_NOTE` còn log server **trống trơn** — không có cách nào biết
nguyên nhân tại chỗ.

`src/ai/intent.py:186` và `src/services/badges.py:186` đã làm đúng
(`logger.exception` / `exc_info`) — chép cùng cách là được.

---

## Ghi chú

Hai lỗi này cùng một kiểu: **nuốt lỗi rồi đi tiếp**. Chúng không làm sập gì nên
không ai thấy, nhưng chúng vô hiệu hoá đúng những thứ được dựng ra để phát hiện
sự cố. Test không bắt được vì mock chặn trước chỗ hỏng.

Không cái nào chặn demo hôm nay — chỉ là các chỉ số sẽ báo 0 nếu ai hỏi tới.
