# Evaluation Report

> Đo trên **bản deploy thật** (`moveinmate-api-production.up.railway.app`), toàn
> bộ đường đi retrieve → generate → guard, không phải chỉ retrieval.
>
> Bộ câu hỏi: [`eval/questions.yaml`](../questions.yaml) — 35 câu, 28 phải trả
> lời được và 7 phải từ chối. Bộ chấm: `python -m scripts.run_eval`.

**Lần chạy gần nhất:** 11/08/2026 · 35 câu · KB 359 chunk

## 1. Kết quả

| Chỉ số | Mục tiêu | Đo được | |
|---|---|---|---|
| **Phân loại đúng** (trả lời vs từ chối) | — | **32/35 · 91%** | ✅ |
| ↳ câu trả lời được | — | 28/28 · 100% | ✅ |
| ↳ câu phải từ chối | — | **4/7 · 57%** | ⚠️ |
| **Đạt trọn vẹn** (đúng loại + đủ ý + có nguồn) | ≥7/10 | **19/35 · 54%** | ❌ |
| Test coverage (pytest) | >60% | **80%** (748 dòng, 150 chưa phủ) | ✅ |
| Latency | <3s | chưa đo | ⏳ |

## 2. Phân tích 16 câu trượt — hai nguyên nhân khác hẳn nhau

### 2.1 Chưa ingest — 9 câu (nguyên nhân lớn nhất, sửa được ngay)

Q09 · Q11 · Q13 · Q15 · Q16 · Q18 · Q19 · Q21 · Q23

Tất cả đều trả lời *"Tôi không tìm thấy thông tin…"* cho những câu mà **đáp án
nằm sẵn trong `data/kb/bql/`** — bốn tài liệu quy trình chưa được nạp vào Chroma.
Index hiện có 359 chunk, chưa bao gồm khoảng 120 chunk của nhóm này.

Đây không phải lỗi mô hình hay lỗi ngưỡng. Chạy `python -m scripts.ingest_kb` là
xong. **Ước tính sau khi ingest: ~28/35 ≈ 80%**, vượt mục tiêu ≥7/10.

Bộ eval đã làm đúng việc của nó: phát hiện dữ liệu chưa vào index, thứ mà nhìn
giao diện không thấy được.

### 2.2 Guard không kích hoạt — 3 câu (vấn đề chất lượng thật)

Q33 · Q34 · Q35 — nhóm *"đúng lĩnh vực nhưng KB không có dữ liệu"*.

```
Q33 "Phí bảo trì 2% của căn hộ tôi là bao nhiêu?"
    answer_source : rag          ← đáng lẽ phải là no_context
    câu trả lời   : "Tôi không tìm thấy thông tin..."
    nguồn kèm theo: Phí dịch vụ VSC 2026, Quy chế TT 05/2024   ← vẫn hiện!
```

Cả ba câu: **LLM tự nhận không biết, nhưng hệ thống vẫn gắn nhãn `rag` và đính
kèm trích dẫn.** Giao diện sẽ hiện khối "Nguồn trích dẫn" ngay dưới một câu trả
lời "tôi không biết".

Nguyên nhân: retrieval trả về đoạn *gần về mặt ngữ nghĩa nhưng không chứa đáp
án* (hỏi phí bảo trì → kéo về trang phí dịch vụ), khoảng cách vẫn dưới
`rag_max_distance = 0.35` nên guard không kích hoạt.

Bốn câu hoàn toàn ngoài lĩnh vực (giá vàng, thời tiết, nấu phở, lãi suất) thì
guard chặn đúng **4/4**. Nghĩa là guard hoạt động ở vùng xa, **hỏng ở vùng biên** —
đúng cảnh báo trong `src/config.py`: hai cụm khoảng cách chỉ cách nhau ~0.04.

**Đây là chế độ hỏng nguy hiểm nhất của sản phẩm.** Câu hỏi nghe hợp lệ, từ vựng
trùng KB, trích dẫn trông đáng tin — người dùng không có cách nào biết là hệ
thống đang không biết.

### 2.3 Lệch từ khoá — 4 câu (chấm quá chặt, không phải lỗi sản phẩm)

Q08 · Q24 · Q27 · Q28 — trả lời **đúng nội dung** nhưng diễn đạt khác từ khoá kỳ
vọng. Ví dụ Q24 liệt kê đủ các bước nhưng gọi bước đầu là *"Lấy số & điền mẫu"*
thay vì *"Tiếp nhận"*.

Cần nới `must_mention` cho nhóm này, hoặc chấp nhận đây là sàn thấp của phép đo.

## 3. Hai việc phải làm, theo thứ tự

1. **Chạy `python -m scripts.ingest_kb`** — vai AI. Xoá 9/16 câu trượt.
2. **Xử lý guard vùng biên.** Vặn ngưỡng xuống là chặn nhầm câu hợp lệ (hai cụm
   chỉ cách 0.04). Hướng đỡ rủi ro hơn: node `generate` phát hiện câu trả lời
   mang nghĩa từ chối thì đổi `answer_source` thành `no_context` và **bỏ trích
   dẫn** — sửa phần hiển thị gây hiểu nhầm trước, hiệu chỉnh ngưỡng sau khi có
   đủ dữ liệu.

## 4. Test tự động

```
pytest -q                  →  80 passed
ruff check src/ tests/     →  All checks passed
pytest --cov=src           →  80%
```

Phủ thấp nhất ở những chỗ test không chạm được nếu không gọi dịch vụ ngoài —
`ingest.py` 0% (cần Google API), `llm.py` 31%, `supabase_admin.py` 46%,
`auth.py` 47% (phần verify chữ ký ES256 đã kiểm chứng riêng bằng token thật).
Tầng API và rule engine — nơi logic nghiệp vụ nằm — đều **100%**.

## 5. Giới hạn của phép đo này

- **35 câu do nhóm tự soạn**, không phải câu hỏi của cư dân thật. Có thiên lệch
  về những gì nhóm biết là có trong KB.
- **Chưa đo latency** và chưa có đánh giá mức độ hài lòng.
- Chấm bằng so khớp từ khoá, không phải người đọc chấm. Câu đúng ý nhưng khác
  chữ bị tính là trượt (mục 2.3).
- Một lần chạy tốn 35 request embedding — đáng kể với hạn mức free tier.
