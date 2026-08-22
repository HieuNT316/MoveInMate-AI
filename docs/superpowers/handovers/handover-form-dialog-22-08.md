# Handover — AI dẫn dắt điền hồ sơ: phần AI đã xong

**Từ:** Hải (AI) · **Cho:** Hiếu (BE), Thu (FE) · **Ngày:** 22/08/2026
**Nối tiếp:** `handover-ai-hai.md` mục 2a + 2c
**Spec:** `../specs/2026-08-20-ai-form-generation-design.md`

---

## 1. Đã làm

| | Việc | File |
|---|---|---|
| 1 | Lớp 3 LLM trong nhận ý định, + **cổng tất định** chặn câu hỏi thông tin | `src/ai/intent.py` |
| 2 | AI hỏi từng trường theo `form_schema.fields[i].question` | `src/ai/form_dialog.py` *(mới)* |
| 3 | Nối vào `POST /chat` | `src/api/routes.py` |
| 4 | Test | `tests/test_intent_detection.py`, `tests/test_form_dialog.py`, `tests/test_api/test_routes.py` |

`pytest -q` → **278 pass** (trước khi sửa: 232 pass / **19 fail**) · `ruff check src/ tests/` sạch.

---

## 2. ⚠️ Ba lỗi đã sửa — `/chat` trước đó hỏng hoàn toàn

Nhánh `NguyenTrungHieu` khi merge về làm **mọi lời gọi `/chat` trả 500**, kể cả
hỏi đáp thường. 19 test đỏ. Ba lỗi cùng một gốc: khối form generation chưa từng
chạy qua HTTP lần nào — unit test gọi thẳng hàm nên không đụng lớp Pydantic.

| | Lỗi | Sửa |
|---|---|---|
| 1 | `routes.py` đọc `payload.checklist_item_id` nhưng `ChatRequest` không khai trường đó → `AttributeError` mọi request | Thêm `checklist_item_id` + `form_data` vào `ChatRequest` |
| 2 | `match.item.id` — khoá chính của `ChecklistItem` tên là `checklist_item_id`, không có `.id` | Dùng đúng tên |
| 3 | Nhánh form trả dict thiếu `conversation_id` và `answer_source` (bắt buộc trong `ChatResponse`), và trả `intent`/`form_schema`/`form_data` mà `ChatResponse` không khai → FE không bao giờ nhận được | Khai đủ trong `ChatResponse` |

**Bài học lặp lại:** thêm ít nhất một test đi qua HTTP thật cho mỗi luồng mới.
Đã thêm `test_luong_dien_ho_so_qua_http`.

---

## 3. Hợp đồng API — thay đổi (Hiếu duyệt, Thu code theo)

Toàn bộ **cộng thêm**, có mặc định, không phá cái đang chạy. FE chưa sửa gì thì
`/chat` hoạt động y như trước.

### `ChatRequest` — thêm 2 trường

```jsonc
{
  "message": "ô tô",
  "conversation_id": "…",
  "checklist_item_id": 42,              // MỚI — đang giữa luồng điền hồ sơ
  "form_data": {"vehicle_type": "Ô tô"} // MỚI — trường đã thu tới lượt trước
}
```

### `ChatResponse` — thêm 4 trường

```jsonc
{
  "answer": "Biển số xe của bạn là gì?",
  "answer_source": "no_context",
  "conversation_id": "…",
  "sources": [],
  "intent": "form_generation",  // MỚI: qa | form_generation | form_review | disambiguation
  "checklist_item_id": 42,      // MỚI
  "form_schema": {...},         // MỚI
  "form_data": {...}            // MỚI
}
```

**Backend không giữ trạng thái.** FE nhận `checklist_item_id` + `form_data` ở
lượt trước, gửi lại nguyên vẹn ở lượt sau. Không có bảng phiên, không có bộ nhớ
server — hội thoại bỏ dở hàng giờ vẫn nối lại được.

### Hai quyết định cần Hiếu xác nhận

1. **`answer_source = "no_context"` cho lượt điền form.** Không thêm giá trị mới
   vào `AnswerSource` vì cột `chat_history.answer_source` là `SAEnum` có ràng
   buộc — thêm là phải migrate. FE phân biệt bằng `intent`, không bằng
   `answer_source`. *Hệ quả cần biết:* `chat_history` không lưu `intent`, nên
   thống kê đếm `no_context` như "lượt hệ thống từ chối" sẽ bị lẫn lượt điền
   form. Muốn tách sạch thì cần thêm cột `intent` — việc của BE, chưa gấp.
2. **Lượt điền form vẫn ghi vào `chat_history`.** Bản cũ `return` sớm trước
   `store.add_chat` nên hội thoại điền hồ sơ biến mất khỏi `/chat/conversations`.

### Đã gộp trùng lặp (chạm file của Hiếu)

- `_ACTION_MARKERS` / `_INFO_TAILS` / `_wants_to_act` chuyển từ `routes.py` sang
  `src/ai/intent.py`, `routes.py` import lại. Vốn từ nhận ý định giờ có **một
  bản duy nhất** — luồng điền form và nút điều hướng buộc phải hiểu cùng một câu
  theo cùng một kiểu. Hành vi nút điều hướng không đổi (test cũ vẫn xanh).
- `_build_form_confirmation` / `_build_disambiguation_message` chuyển sang
  `form_dialog.py` (vai AI giữ phần soạn lời).

---

## 4. Cổng tất định — phần quan trọng nhất, đọc kỹ

Bản trước: lớp 3 **luôn** trả `ambiguous=True`. Nghĩa là mọi câu không trùng tên
thủ tục nào đều bị trả lời bằng *"Có nhiều thủ tục phù hợp. Bạn muốn: 1… 2…"* —
**US-05 (hỏi đáp kèm nguồn, đang đo 32/35) ngừng hoạt động** ngay khi có
`form_schema` trong DB.

`ProcedureMatch` nay có đủ **ba** trạng thái:

| Trạng thái | Nghĩa |
|---|---|
| `item` có giá trị | Vào luồng điền form |
| `item=None, ambiguous=True` | Khớp nhiều thủ tục → hỏi lại |
| `item=None, ambiguous=False` | **Không phải ý định làm thủ tục → nhường RAG** ← trạng thái còn thiếu |

Thứ tự xử lý:

```
is_info_question(câu)?  ──yes──►  nhường RAG        (0 lượt LLM)
   │ no
Lớp 1 keyword ─► khớp đúng 1 ─► vào form            (0 lượt LLM)
Lớp 2 fuzzy   ─► khớp đúng 1 ─► vào form            (0 lượt LLM)
              └─► khớp >1    ─► hỏi lại             (0 lượt LLM)
   │ không khớp
has_action_marker(câu)? ──no──►  nhường RAG         (0 lượt LLM)
   │ yes
Lớp 3 LLM ─► tên khớp khít danh sách ─► vào form
          └─► khác/lỗi              ─► nhường RAG
```

Hai điều cố ý:

- **Câu hỏi thông tin bị chặn TRƯỚC lớp 1.** *"Đăng ký thẻ xe cần giấy tờ gì?"*
  có tên thủ tục nằm nguyên trong câu nên lớp 2 sẽ khớp — không chặn trước thì
  người ta hỏi giấy tờ mà nhận về một cái form.
- **LLM chỉ được CHỌN trong danh sách đóng, không được ĐẶT TÊN.** Chuỗi trả về
  phải trùng khít một `task_name` có thật; thêm lời dẫn, đổi hoa thường, hay bịa
  tên đều bị loại. Cùng lập luận đã áp cho `sources[]` và cho `_match_checklist_item`.
  LLM lỗi/timeout → nhường RAG, không ném lỗi làm sập `/chat`.

Chi phí: câu hỏi thường **không tốn lượt gọi LLM nào**. Có test khẳng định
(`assert fake_llm.calls == 0`).

---

## 5. Cách AI hỏi (`form_dialog.py`)

Hỏi lần lượt theo **đúng thứ tự khai trong `schema.fields`** — người soạn schema
quyết định mạch hội thoại, không phải code. Câu hỏi lấy nguyên văn từ
`field.question`, ghép thêm gợi ý (danh sách lựa chọn / "có thể bỏ qua").

```
Cư dân: Tôi muốn đăng ký thẻ xe
AI:     Bạn muốn làm thủ tục **Đăng ký thẻ xe**. Tôi hỏi bạn vài thông tin nhé.
        Bạn đăng ký thẻ xe gì? (Ô tô / Xe máy)
Cư dân: ô tô
AI:     Biển số xe của bạn là gì?
Cư dân: không nhớ
AI:     Biển số xe "không nhớ" chưa đúng định dạng hệ thống nhận. …
        Biển số xe của bạn là gì?              ← hỏi LẠI đúng trường đó
Cư dân: 30a-123.45
AI:     Bạn cần làm bao nhiêu thẻ? (không bắt buộc — nhắn "bỏ qua" để mặc định 1)
Cư dân: hai cái
AI:     [bản tóm tắt + danh sách giấy tờ cần đính kèm]  → intent=form_review
```

Đọc câu trả lời: `select` khớp theo **ranh giới từ** (không phải chuỗi con — bỏ
dấu xong "Ô tô" thành "o to" và đụng trúng giữa câu "cho tôi nộp"), `number`
nhận cả chữ ("hai cái" → 2), trường không bắt buộc nhắn "bỏ qua" thì dùng
`default`, trường có `pattern` được dọn hoa thường/khoảng trắng trước khi so.

**Nhặt sẵn từ câu mở đầu** cố ý dè dặt: chỉ nhận `select` và trường có `pattern`
(tự kiểm được). Trường chữ tự do thì hỏi, không đoán — gán cả câu *"Tôi muốn
đăng ký thẻ xe"* vào ô "Biển số xe" tệ hơn hẳn hỏi thêm một lượt.

**Module không ghi gì vào DB.** Chỉ trả `form_data` về FE; cư dân xác nhận rồi
FE mới gọi `POST /applications`. Người chốt hồ sơ vẫn là cư dân (spec 5.3).

---

## 6. Việc còn lại

### Thu (FE) — tính năng chưa dùng được cho tới khi làm xong

`web/lib/api.ts` chưa khai `intent` / `form_schema` / `form_data`, và `sendChat`
chưa gửi `checklist_item_id` / `form_data`. **Hệ quả: cư dân trả lời câu hỏi của
AI thì mỗi lượt lại quay về câu hỏi đầu tiên** — vì FE không gửi lại state.

Đúng kiểu lỗi đã xảy ra 11/08 (*"BE đã trả field này từ 10/08 nhưng FE không khai
type nên bỏ qua hoàn toàn"*). Cần:

1. Thêm `intent`, `checklist_item_id`, `form_schema`, `form_data` vào `ChatAnswer`.
2. `sendChat` nhận và gửi kèm `checklist_item_id` + `form_data`.
3. `intent === "form_review"` → mở `FormReviewDialog` với `form_data` đã có.

### Hiếu (BE) — ba việc

| | Việc | Vì sao |
|---|---|---|
| a | **`pattern` biển số sai** trong `scripts/seed_form_schema.py`: `^[0-9A-Z\-]{5,15}$` **không nhận dấu chấm**, nên từ chối đúng "30A-123.45" (ví dụ trong spec) và "29P1-123.45" (câu eval FG01). Sửa thành `^[0-9A-Z\-\.]{5,15}$` rồi chạy lại `python -m scripts.seed_form_schema` | Không sửa thì mọi biển số thật đều bị từ chối ở bước hỏi biển số |
| b | `src/ai/form_extraction.py` **không còn được gọi từ đâu** — `form_dialog.seed_from_message` thay thế (dè dặt hơn: bản cũ gán tin nhắn cuối cho mọi trường chữ, nên form có ≥2 trường chữ thì chúng giành nhau đúng một câu). Đề nghị xoá cùng `tests/test_form_extraction.py` | Code chết trên `main` — đúng thứ mục 12 dặn tránh |
| c | `scripts/run_eval.py` chỉ hiểu `expect: answer\|refuse`. FG01/FG02 khai `expect: form_generation\|disambiguation` nên **bị loại khỏi cả hai nhóm thống kê**, chạy eval không đo gì | Hai câu eval hiện không có tác dụng |

### Tôi (Hải) — chưa làm, đã cân nhắc và cố ý bỏ

- **FG02 *"Làm thẻ cư dân cho tôi"* hiện không kích hoạt disambiguation.** Câu này
  không có dấu hiệu hành động nào trong `_ACTION_MARKERS` nên cổng tất định
  nhường cho RAG. Nới danh sách marker sẽ đổi cả hành vi nút điều hướng (đang có
  test) và tăng rủi ro nuốt câu hỏi thường. **Ưu tiên giữ US-05 an toàn** —
  đề nghị bàn cả nhóm trước khi nới.
- **`detect_procedure_intent` tra trên TOÀN BỘ `checklist_items`, không phải
  checklist riêng của người dùng.** Nghĩa là người thuê có thể bị dẫn vào form
  "Làm thẻ cư dân (chủ hộ)". `_match_checklist_item` (nút điều hướng) đã lọc
  đúng qua `generate_checklist(user, …)`; chỗ này thì chưa. Cần truyền `user`
  vào — **đụng ranh giới BE/AI, chờ chốt rồi làm.**
- **Không có lối thoát giữa chừng.** Đang điền hồ sơ mà cư dân hỏi sang chuyện
  khác (*"à mà phí bảo trì bao nhiêu?"*) thì câu đó bị đọc thành câu trả lời cho
  trường đang hỏi. Chưa sửa vì lối thoát kéo theo câu hỏi "quay lại thì vào lại
  từ đâu" — cần chốt cùng Thu vì phần lớn nằm ở giao diện (nút *Huỷ*, hoặc giữ
  form ở panel riêng thay vì trong dòng chat). Đáng bàn trước khi quay video.
- **Chạy lại `run_eval`** — nên làm sau khi (a) và (c) xong, không thì số đo
  không phản ánh hệ thống thật.

---

## 7. Lưu ý vận hành

`data/chroma/` đang bẩn từ trước phiên làm việc này (`length.bin`,
`chroma.sqlite3`). Tôi **không** chạy `git checkout -- data/chroma/` vì chưa xác
minh được lần ingest gần nhất — làm sai thứ tự là xoá mất kết quả ingest (đã xảy
ra 11/08). Kiểm `collection.count()` trước khi dọn.
