# Kế hoạch đánh giá MoveInMate

## Chạy đánh giá

```bash
# Bản cục bộ
python -m scripts.run_eval

# Bản production
python -m scripts.run_eval --api https://moveinmate-api-production.up.railway.app/api/v1

# Thử nhanh vài câu
python -m scripts.run_eval --limit 5
python -m scripts.run_eval --api https://... --limit 5
```

## Hai hệ thống chấm điểm

### 1. Chấm từ khoá (keyword grading) — luôn chạy

Mỗi câu hỏi đều được đánh giá theo ba tiêu chí cứng:

| Tiêu chí | Ý nghĩa |
|---|---|
| **Đúng loại** | Câu cần trả lời thì `answer_source` phải là `rag`/`faq`; câu ngoài phạm vi phải trả về `no_context` |
| **Đủ ý** | Câu trả lời chứa đủ từ khoá bắt buộc trong `must_mention` |
| **Có nguồn** | Câu trả lời được kèm ít nhất một trích dẫn; câu từ chối thì không được kèm trích dẫn |

**Pass rate** = số câu đạt cả ba tiêu chí / tổng số câu.

### 2. LLM judge — chạy song song

Với mỗi câu, một LLM thứ hai (cùng model mà app dùng: `gpt-4o-mini` qua OpenAI hoặc OpenRouter) đóng vai trò chuyên gia đánh giá:

**Với câu cần trả lời** (`expect: answer`):

- `correctness`: "Câu trả lời có chứa thông tin ĐÚNG về mặt sự thật không?"
- `citation`: "Câu trả lời có trích dẫn nguồn PHÙ HỢP không?"

**Với câu từ chối** (`expect: refuse`):

- `correctness`: "Việc từ chối này CÓ HỢP LÝ không?"

Judge trả về một trong: `ĐÚNG / SAI / KHÔNG CHẮC CHẮN / KHÔNG ÁP DỤNG`.

**Chi phí**: ~35 lần gọi judge × ~$0.004/câu = **~$0.14** cho 35 câu.

**Timeout**: 15 giây mặc định của `llm_timeout_seconds`. Nếu judge lỗi, câu đó được chấm keyword-only, không fail cả lượt đánh giá.

## Chỉ số tổng hợp

Sau mỗi lần chạy, script in ra:

```
Tong the         : 31/35 (89%)
Dung loai        : 32/35 (91%)
  cau tra loi duoc: 27/31
  cau phai tu choi: 5/5

LLM judge (n=35, loi=0):
  correctness     : 30/35 (86%)
  citation        : 28/31 (90%)
```

| Trường | Ý nghĩa |
|---|---|
| `keyword.pass_rate` | Tỷ lệ câu đạt đủ ba tiêu chí keyword |
| `llm_judge.correct_rate` | Tỷ lệ câu judge đánh là ĐÚNG (trên tổng câu được judge thành công) |
| `llm_judge.cite_rate` | Tỷ lệ citation ĐÚNG hoặc KHÔNG ÁP DỤNG (chỉ tính câu trả lời, không tính refuse) |
| `llm_judge.judge_errors` | Số câu judge thất bại (fallback về keyword-only) |

## Theo dõi regression

Script tự động so sánh với lần chạy mới nhất trong `eval/results/`:

- Tìm file `run-*.json` mới nhất (không tính `-metrics.json`)
- So sánh `llm_correct_rate` hiện tại với lần trước
- Nếu giảm **>= 5 điểm phần trăm**: in cảnh báo

```
WARNING  REGRESSION: LLM accuracy dropped 12% (67% -> 55%) vs run-20260812-0734
```

- Nếu giảm < 5 điểm: in thông tin nhỏ

```
INFO     LLM accuracy down 3% (67% -> 64%) vs run-20260812-0734 — within threshold
```

## Output files

| File | Nội dung |
|---|---|
| `eval/results/run-YYYYMMDD-HHMM.json` | Chi tiết đầy đủ, mỗi câu một object |
| `eval/results/run-YYYYMMDD-HHMM-metrics.json` | Chỉ số tổng hợp (dùng cho regression) |

## Giới hạn đã biết

1. **LLM judge là mô hình cùng loại** — judge và app dùng chung model nên không phải độc lập thực sự. Giám sát kết quả judge để phát hiện drift.

2. **Citation không đo lường bằng keyword** — một câu có thể được judge là citation ĐÚNG nhưng keyword đánh là `cited_ok=false` (hoặc ngược lại) vì hai hệ thống dùng tiêu chí khác nhau.

3. **`pass_rate` của keyword có thể cao hơn thực tế** — vì câu trả lời có thể chứa từ khoá đúng mà vẫn sai về nội dung. LLM judge phát hiện được điều này.

4. **Judge phụ thuộc ngữ cảnh** — nếu câu trả lời bị cắt (giới hạn 300 ký tự trong JSON), judge có thể đánh giá không chính xác.

5. **Không đo guard effectiveness riêng** — `right_kind` phụ thuộc vào cả retrieval lẫn guard cùng lúc; không tách riêng được ảnh hưởng của từng thành phần.
