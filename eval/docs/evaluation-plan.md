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

Với mỗi câu, một LLM **độc lập** đóng vai trò chuyên gia đánh giá:
`anthropic/claude-sonnet-5` qua OpenRouter (`JUDGE_MODEL` trong
`scripts/run_eval.py`) — **cố ý khác** `gpt-4o-mini` đang sinh câu trả lời.

Bản trước dùng chung một model cho cả hai việc. Kết quả: **100% ở cả ba tiêu
chí** — model tự chấm bài mình thì khen chính nó. Đổi sang giám khảo độc lập,
cùng hệ thống đó chấm được 48,6% đúng nội dung. Con số 100% từng được coi là
thành tích, thực chất là lỗi phương pháp.

Giám khảo được xem **toàn bộ chunk đã truy xuất** (`_fetch_full_context`), không
phải `sources[]` mà `/chat` trả về — cái đó đã gộp theo `document_id` và cắt còn
220 ký tự mỗi tài liệu để hiển thị cho người dùng. Chấm trên bản cắt đó thì phạt
oan mọi câu trả lời viện tới phần nội dung nằm ngoài 220 ký tự (đo được: citation
35,7% → 100% sau khi sửa).

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

## Đánh giá bằng RAGAS (`scripts/run_ragas.py`)

Bộ chỉ số chuẩn ngành, chạy song song hệ chấm ở trên. Khác biệt: `run_eval`
chấm bằng từ khoá và một prompt giám khảo tự viết — số ra chỉ so được với
chính dự án này. RAGAS tách câu trả lời thành từng mệnh đề rồi kiểm từng
mệnh đề theo phương pháp đã công bố, nên số so được với dự án khác.

```bash
python -m scripts.run_ragas                                   # chạy đủ, gọi /chat
python -m scripts.run_ragas --samples-in <file>-samples.json  # chấm lại mẫu cũ
```

**Chỉ chấm 28/37 câu.** Bảy câu `expect: refuse` bị loại có chủ đích: hệ thống
từ chối đúng thì `retrieved` rỗng, mà cả ba chỉ số đều đo quan hệ giữa câu trả
lời và ngữ cảnh — không có ngữ cảnh thì không có gì để đo, ép chấm sẽ cho 0
điểm đúng vào lúc hệ thống làm đúng. Hai câu FG (luồng điền hồ sơ) không đi
qua RAG. Chín câu đó vẫn được `run_eval.py` chấm bằng tiêu chí phù hợp.

### Kết quả 05/09/2026

| Chỉ số | Điểm | Mẫu đo được |
|---|---|---|
| `faithfulness` — mỗi ý có bám tài liệu truy xuất không | **0,990** | 20/20 |
| `answer_relevancy` — có đúng trọng tâm câu hỏi không | **0,844** | 20/20 |
| `context_precision` — đoạn lấy về có dùng được không | **0,889** | 20/20 |

Giám khảo `anthropic/claude-sonnet-5`, embeddings `gemini-embedding-001`.
Không mẫu nào lỗi trong ba chỉ số trên — `failed_samples = 0`.

**Mẫu là 20/28 câu, không phải 28/28.** Tám câu Q11–Q14, Q25–Q28 không đo được
vì hạn mức tài khoản OpenRouter (429 ở bước gọi `/chat`, rồi 402
`in_flight_budget_exhausted` ở bước chấm), **không phải vì hệ thống trả lời
kém**. File kết quả có thêm khối `estimate_full_set` suy ra điểm cho 28 câu
bằng *mean imputation* — lưu ý điểm suy ra **bằng đúng** điểm đo trên 20 câu,
phép điền không tạo thông tin mới, và độ lệch chuẩn trên tập đã điền nhỏ hơn
thực tế. Báo cáo con số đó thì phải kèm chữ "ước lượng trên mẫu 20/28".

Mẫu của 28 câu đã lưu tại `eval/results/ragas-20260905-1208-samples.json`
(riêng 8 câu thiếu: `ragas-20260905-thieu8-samples.json`). Nạp credit rồi chạy
lại bằng `--samples-in` là có số đo thật, không tốn thêm lượt embedding Google.

### Hai cái bẫy đã làm hỏng bốn lượt đo

**1. OpenRouter giữ chỗ credit theo `max_tokens`, không theo lượng token thật
dùng.** Không đặt `max_tokens` thì nó lấy trần đầu ra của model (sonnet-5:
65 536 token) để giữ chỗ → số dư vài chục cent là mọi request bị 402 dù câu
trả lời thật chỉ dài vài trăm token. Vì vậy `_get_judge_llm` nhận tham số
`max_tokens` và `run_ragas` đặt 8192. Đặt quá thấp (đã thử 2048) lại sinh
`LLMDidNotFinishException` — giám khảo bị cắt giữa chừng, RAGAS bỏ luôn mẫu đó.

**2. RAGAS lặng lẽ bỏ mẫu lỗi ra khỏi trung bình.** Lượt chạy 16 luồng mặc
định có 17/60 phép chấm chết vì 402, kết quả in ra `faithfulness 1.000` — số
đẹp vì thất bại bị giấu, không phải vì hệ thống tốt; câu khó chính là câu dễ
chết nên phần sống sót lệch về phía dễ. Script nay in `scored_samples` /
`failed_samples` cho **từng** chỉ số và đánh dấu chỉ số nào không đầy đủ.
**Chỉ số có `failed_samples` > 0 thì không đem lên slide.**

## Giới hạn đã biết

1. **Vẫn là LLM chấm LLM** — giám khảo nay đã độc lập (`claude-sonnet-5` chấm bài của `gpt-4o-mini`, xem mục LLM judge), nên hết thiên vị tự chấm; nhưng giám khảo vẫn là mô hình ngôn ngữ, không phải người, và có thể sai theo cách riêng của nó. Giám sát kết quả judge để phát hiện drift.

2. **Citation không đo lường bằng keyword** — một câu có thể được judge là citation ĐÚNG nhưng keyword đánh là `cited_ok=false` (hoặc ngược lại) vì hai hệ thống dùng tiêu chí khác nhau.

3. **`pass_rate` của keyword có thể cao hơn thực tế** — vì câu trả lời có thể chứa từ khoá đúng mà vẫn sai về nội dung. LLM judge phát hiện được điều này.

4. **Judge phụ thuộc ngữ cảnh** — nếu câu trả lời bị cắt (giới hạn 300 ký tự trong JSON), judge có thể đánh giá không chính xác. Phía *ngữ cảnh* đã sửa: giám khảo được xem toàn bộ chunk truy xuất chứ không phải bản cắt 220 ký tự trong `sources[]`.

5. **RAGAS mới phủ 20/28 câu** — thiếu Q11–Q14, Q25–Q28 vì hạn mức tài khoản, không phải vì chất lượng trả lời. Xem mục RAGAS ở trên.

6. **Không đo guard effectiveness riêng** — `right_kind` phụ thuộc vào cả retrieval lẫn guard cùng lúc; không tách riêng được ảnh hưởng của từng thành phần.
