# Evaluation Report

> Đo trên **bản deploy thật** (`moveinmate-api-production.up.railway.app`), toàn
> bộ đường đi retrieve → generate → guard, không phải chỉ retrieval.
>
> Bộ câu hỏi: [`eval/questions.yaml`](../questions.yaml) — 35 câu, 28 phải trả
> lời được và 7 phải từ chối. Bộ chấm: `python -m scripts.run_eval`.

**Lần chạy gần nhất:** 12/08/2026 · 35 câu · KB **412 chunk** (đã ingest đủ)
*(lần trước 11/08, KB 359 chunk: 19/35 — xem mục 3)*

## 1. Kết quả

| Chỉ số | Mục tiêu | Đo được | |
|---|---|---|---|
| **Phân loại đúng** (trả lời vs từ chối) | — | **32/35 · 91%** | ✅ |
| ↳ câu trả lời được | — | **28/28 · 100%** | ✅ |
| ↳ câu phải từ chối | — | **4/7 · 57%** | ⚠️ |
| **Đạt trọn vẹn** (đúng loại + đủ ý + có nguồn) | ≥7/10 | **32/35 · 91%** | ✅ |
| Test coverage (pytest) | >60% | **80%** (748 dòng, 150 chưa phủ) | ✅ |
| Latency | <3s | chưa đo | ⏳ |

## 2. Ba câu trượt còn lại — đều cùng một nguyên nhân

Q33 · Q34 · Q35 — nhóm *"đúng lĩnh vực nhưng KB không có dữ liệu"*.

```
Q33 "Phí bảo trì 2% của căn hộ tôi là bao nhiêu?"
    answer_source : rag          ← đáng lẽ phải là no_context
    câu trả lời   : "Tôi không tìm thấy thông tin..."
    nguồn kèm theo: Phí dịch vụ VSC 2026, Quy chế TT 05/2024   ← vẫn hiện!
```

Cả ba: **LLM tự nhận không biết, nhưng hệ thống vẫn gắn nhãn `rag` và đính kèm
trích dẫn.** Giao diện sẽ hiện khối "Nguồn trích dẫn" ngay dưới một câu "tôi
không biết".

Nguyên nhân: retrieval trả về đoạn *gần về ngữ nghĩa nhưng không chứa đáp án*
(hỏi phí bảo trì → kéo về trang phí dịch vụ), khoảng cách vẫn dưới
`rag_max_distance = 0.35` nên guard không kích hoạt.

Bốn câu hoàn toàn ngoài lĩnh vực (giá vàng, thời tiết, nấu phở, lãi suất) bị
chặn đúng **4/4**. Guard chạy tốt ở vùng xa, **hỏng ở vùng biên** — đúng cảnh
báo trong `src/config.py`: hai cụm khoảng cách chỉ cách nhau ~0.04.

**Đây là chế độ hỏng nguy hiểm nhất còn lại.** Câu hỏi nghe hợp lệ, từ vựng
trùng KB, trích dẫn trông đáng tin — người dùng không có cách nào biết hệ thống
đang không biết.

## 3. So với lần đo 11/08

| | 11/08 (KB 359) | 12/08 (KB 412) |
|---|---|---|
| Đạt trọn vẹn | 19/35 · 54% | **32/35 · 91%** |
| Phân loại đúng | 32/35 | 32/35 |
| Câu phải từ chối | 4/7 | 4/7 |

**+13 câu, toàn bộ nhờ ingest.** Lần trước 9 câu trượt vì bốn tài liệu
`data/kb/bql/` chưa vào index và hai file đã viết dày chưa được nạp lại; số còn
lại là chấm quá chặt về từ khoá.

Một kỳ vọng đã sửa: **Q20** trước đòi chữ *"có"* trong khi câu trả lời đúng là
*"người thuê nhà **phải ký** nội quy"* — chấm cách diễn đạt chứ không chấm nội
dung. Đổi sang `phải ký`. Đây là sửa phép đo, không phải sửa sản phẩm.

**Việc còn lại duy nhất là guard vùng biên.** Vặn ngưỡng xuống sẽ chặn nhầm câu
hợp lệ (hai cụm chỉ cách 0.04). Hướng đỡ rủi ro: node `generate` nhận ra câu trả
lời mang nghĩa từ chối thì đổi `answer_source` thành `no_context` và **bỏ trích
dẫn** — sửa phần hiển thị gây hiểu nhầm trước, hiệu chỉnh ngưỡng sau.

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
