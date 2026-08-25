# Cổng nhận ý định đang nuốt câu hỏi của RAG — đã sửa

**Từ:** Hải (AI) · **Cho:** Hiếu (BE) · **Ngày:** 25/08/2026
**File đã sửa:** `src/ai/intent.py` (chỉ file này) · `pytest -q` → **323 pass**

---

## 1. Việc Hiếu cần làm — ba thứ, đọc trước khi làm gì khác

| | Việc | Vì sao gấp |
|---|---|---|
| A | **Kiểm xem đã chạy `seed_form_schema` trên Supabase chưa.** Rồi → bản deploy đang dính lỗi dưới đây, cần deploy lại sau khi merge nhánh này. Chưa → nó sẽ hỏng ngay lúc anh chạy | Lỗi chỉ kích hoạt khi `checklist_items.form_schema` có dữ liệu |
| B | **Đừng chạy `run_eval` trước khi bản sửa này lên deploy.** Số sẽ tệ thảm và trông y như RAG hỏng | 14/35 câu bị chấm nhầm thành "từ chối" |
| C | Đọc mục 4 — **kế hoạch AI Phase 2 có 6 chỗ chưa chạy được** | Tránh viết rồi bỏ |

---

## 2. Chuyện gì đã xảy ra

Luồng điền hồ sơ chạy **trước** RAG. Cổng nhận ý định quyết định câu nào vào
form, câu nào nhường cho RAG. Cổng đó nhận nhầm quá nhiều.

Đo bằng cách chạy cả 37 câu `eval/questions.yaml` qua đúng cổng đó, trên đúng
dữ liệu `seed_data` + `seed_form_schema`:

```
Tổng 37 câu · bị luồng form giữ lại: 16   (chỉ FG01, FG02 là đúng)
→ 14 câu hỏi thật không bao giờ tới được RAG
```

Nặng nhất là **Q31 `"Cho tôi công thức nấu phở bò."`**:

```
keywords: ['cong', 'thuc', 'nau', 'pho']
  'pho' -> ['Kích hoạt thẻ phòng gym']   <== khớp 1, chốt high confidence
```

`"phở"` bỏ dấu thành `"pho"`, nằm lọt trong `"phòng"` → `"phong"`. Q31 chính là
**bước 7 kịch bản demo** — câu chứng minh hệ thống từ chối thay vì bịa, thứ
`ROLES_AND_PLAN` mục 8 gọi là *"chỗ ăn điểm nhất"*. Nó mở form đăng ký gym.

**Không có gì báo động.** `/chat` vẫn trả 200, test vẫn xanh; chỉ có
`answer_source` lặng lẽ thành `no_context`. Đúng kiểu hỏng thầm lặng.

Lỗi này **có trước** phần form dialog của tôi — lớp keyword là bản gốc từ Task 3.
Nó chỉ lộ ra khi `form_schema` được seed cho 9 thủ tục.

---

## 3. Đã sửa thế nào

**Bỏ hẳn lớp "khớp một từ khoá đơn".** Lớp cũ tách từ 3+ ký tự khỏi câu hỏi, từ
nào nằm trong đúng một tên thủ tục thì chốt luôn. Đo trên cả 37 câu: gây **11
trong 15** ca nhận nhầm, khớp toàn từ vu vơ — `thue`, `nguoi`, `may`, `hong`,
`dinh`, `vao`, `boi`, `pho`.

Nó còn **không cứu được ca nào**: FG01 *"…thẻ **xe máy**…"* bị `may` kéo về
*"thẻ thang **máy**"* — giữ được câu hỏi nhưng mở sai thủ tục. Bỏ lớp này thì
lớp 2 khớp đúng "Đăng ký thẻ xe".

**Bổ sung 10 đuôi câu hỏi** vào cổng chặn: `nhung gi`, `lam sao`, `o dau`,
`nao xu ly`, `bao lau`, `duoc khong`, `co phai`, `co duoc`, `hay khong`,
`phai lam gi`. Mỗi chuỗi là một câu hỏi thật đã bị nhận nhầm.

Kết quả sau khi sửa:

```
{'GATE-info': 29, 'GATE-noaction': 6, 'L2-core': 1, 'L2-ambig': 1}
→ 0 ca sai · FG01 khớp đúng "Đăng ký thẻ xe" · FG02 vẫn hỏi lại 2 nhánh
```

**Recall có mất gì không?** Tên thủ tục dài hơn câu người ta gõ (vd *"Đăng ký
internet và truyền hình"* vs *"tôi muốn đăng ký internet"*) giờ không khớp tất
định nữa — **lớp 3 LLM gánh phần đó**. Lớp 3 chỉ chạy khi câu có dấu hiệu hành
động, nên câu hỏi thường vẫn không tốn lượt gọi nào.

**Chốt chặn mới:** `tests/test_intent_vs_eval.py` chạy cả 37 câu eval qua cổng
mỗi lần CI chạy. Đã kiểm chứng test không rỗng — phá tạm cổng info thì 11 test
đỏ ngay.

---

## 4. Kế hoạch `2026-08-25-ai-phase2.md` — 6 chỗ chưa chạy được

Nói trước khi có người bắt tay vào viết.

| | Vấn đề | Hậu quả |
|---|---|---|
| 1 | `@require_permission(Permission.MANAGE_FAQ)` (Task 2) — grep toàn `src/` không có | `NameError` lúc import |
| 2 | Task 4 viết lại `rag_retrieve_node` theo shape `retrieved["count"]` / `["max_distance"]` — không phải hàm thật | Áp nguyên vào là hỏng node đang chạy |
| 3 | Task 4 trả `sources` **kèm** câu "chưa tìm thấy thông tin" | Dựng lại đúng bug V3/B5 mà charter mục 11 gọi là *"chế độ hỏng nguy hiểm nhất còn lại"* |
| 4 | `RAG_MAX_DISTANCE = 0.35` viết cứng, đã có `settings.rag_max_distance` | Hai nguồn sự thật cho một ngưỡng |
| 5 | Test `patch("src.services.store.db")` — `store.py` không có biến `db` cấp module | Test viết ra là đỏ |
| 6 | `faq_node` tự mở `SessionLocal()` bên trong node | Phá bất biến ghi ở `src/agents/state.py`: *"graph không chạm DB; route resolve tiếp"* |

**Thêm hai thứ về dữ liệu:** bảng `faq` đang **rỗng**, `seed_data` không sinh FAQ,
`store.py` không có hàm FAQ nào. Node FAQ chạy đúng đến mấy thì demo vẫn không
thấy gì — cần người soạn nội dung FAQ trước, và đó là việc dữ liệu. Đây cũng
đúng lý do charter mục 13 từng **bỏ US-09**: *"làm CRUD cho thứ chưa ai đọc là
công vô ích."*

---

## 5. Phần tôi làm tiếp, không chặn ai

Theo ý "phần nào song song được thì làm trước":

| | Việc | File | Trạng thái |
|---|---|---|---|
| 1 | Cổng nhận ý định | `src/ai/intent.py` | **Xong** |
| 2 | Guard vùng biên (C2/V3/B5) | `src/agents/nodes/generate.py` | **Xong** |
| 3 | LangSmith (V1/E3/B8) | `src/services/tracing.py`, config, main | **Xong** |
| 4 | Node FAQ | `src/agents/nodes/faq_lookup.py`, `graph.py`, `state.py` | **Xong — chờ 1 seam của anh** |
| 5 | Chạy lại `run_eval` | `eval/` | Chờ deploy bản này |

`pytest -q` → **341 pass** · ruff sạch trên mọi file tôi đụng.

### Việc 2 — guard vùng biên

Guard chống bịa nay có **hai tầng**: (1) `retrieved` rỗng → không gọi LLM, như
cũ; (2) có tài liệu nhưng LLM tự nhận không trả lời được → cũng đổi thành câu
từ chối chuẩn, `answer_source="no_context"`, **và bỏ `sources`**.

Nhận diện ưu tiên **mã quy ước** `KHONG_CO_TRONG_TAI_LIEU` (prompt yêu cầu LLM
phát ra), lưới dự phòng là vài cách nói thẳng, và chỉ tính khi câu đủ ngắn —
câu DÀI có chữ "không đề cập" gần như luôn là trả lời được một phần
("Tài liệu không đề cập phí X, **nhưng có nêu** Y"), đổi nó thành từ chối là
vứt mất phần Y. Có test cho cả hai chiều.

**Móc cho Task 4 đã đặt sẵn** trong `_refuse()` — đó chính là chỗ hệ thống biết
mình không trả lời được, tức chỗ nên gợi ý tạo ticket. Chưa cắm vì
`store.create_ticket` chưa có.

### Việc 3 — LangSmith: mắt xích còn thiếu hoá ra rất nhỏ

Ba biến `LANGCHAIN_*` đã nằm trong `.env.example` từ lâu mà **chưa từng có tác
dụng**: LangChain đọc cấu hình tracing từ `os.environ`, còn pydantic-settings
chỉ nạp `.env` vào đối tượng `Settings` chứ không export ra environ. Không thiếu
thư viện nào cả, chỉ thiếu bước bắc cầu.

`src/services/tracing.py` làm việc đó, gọi ở `main.py` trước khi dựng app.
Thiếu `LANGCHAIN_API_KEY` mà vẫn bật thì nó **tự tắt và ghi cảnh báo** thay vì
để LangChain ném lỗi ở mọi lượt gọi LLM. Không in key ra log.

⚠️ `.env.example` đổi mặc định thành `LANGCHAIN_TRACING_V2=false`: bật là mỗi
lượt chat gửi prompt và câu hỏi của cư dân sang dịch vụ ngoài. Bật khi cần cho
mentor xem trace.

### Việc 4 — node FAQ, và seam anh cần làm

Node **không chạm DB**: nhận danh sách FAQ qua `ChatState.faqs`, y như
`chat_history`. Nhờ vậy tôi làm xong trước migration của anh, và test được bằng
dữ liệu tiêm vào.

**Rỗng `faqs` thì node là no-op** — đúng trạng thái hiện tại (bảng `faq` chưa có
dữ liệu), nên merge vào không đổi hành vi gì. 341 test cũ vẫn xanh nguyên.

**Seam duy nhất anh cần cung cấp:**

```python
# src/services/store.py
def get_active_faqs(db: Session) -> list[dict[str, Any]]:
    """[{"faq_id": int, "question": str, "answer": str}], is_active=True, theo order_index."""
```

Rồi một dòng ở route, cạnh chỗ đã dựng `recent_turns`:

```python
state = await chat_graph.ainvoke({
    "query": payload.message,
    "chat_history": recent_turns,
    "faqs": store.get_active_faqs(db),   # thêm dòng này
})
```

Graph nay là: `rewrite_query → faq_lookup → (khớp? END : rag_retrieve → generate)`.
FAQ đứng **sau** `rewrite_query` để câu tiếp nối ("còn phí thì sao?") được viết
lại thành câu độc lập trước khi đem so.

**Ngưỡng `faq_min_similarity` mặc định 0.5 và CHƯA hiệu chỉnh trên dữ liệu thật**
— chưa có FAQ nào để hiệu chỉnh. Đặt cao có chủ ý vì FAQ trả lời **không kèm
trích dẫn**: khớp lỏng là cướp mất câu mà RAG lẽ ra trả lời được kèm nguồn, tức
ăn vào đúng ràng buộc lõi của US-05.

Về cách so, tôi đã đo và chọn ngược trực giác — **giữ dấu, không bỏ stopword**:

| Câu người dùng (đối chiếu FAQ *"Làm thẻ cư dân như thế nào?"*) | bỏ dấu + bỏ stopword | cách đang dùng |
|---|---|---|
| "Làm thẻ cư dân thế nào?" | 1.000 | 0.857 |
| "Mất thẻ cư dân thì làm sao?" | **0.667** | **0.400** |

Câu thứ hai là câu hỏi khác hẳn — mất thẻ không phải làm thẻ. Ở ngưỡng 0.5, cách
bỏ dấu + bỏ stopword khớp cả hai, tức trả hướng dẫn *làm thẻ* cho người vừa
*mất thẻ*. Sai mà nghe rất trôi chảy. Có test khoá ca này.

Đánh đổi: gõ không dấu sẽ không khớp FAQ nào và rơi xuống RAG — chiều sai an
toàn, RAG vẫn trả lời và còn kèm nguồn.

**`answer_source="faq"` cần Thu gắn nhãn** ("Câu hỏi thường gặp") thay vì để
trống chỗ nguồn trích dẫn. Giá trị này đã có sẵn trong `AnswerSource` từ đầu nên
không đổi hợp đồng; logic `refused` hiện tại của FE cũng không bị ảnh hưởng.

### Còn thiếu để nhánh FAQ thật sự chạy

Ngoài seam trên: **nội dung FAQ**. Bảng rỗng, `seed_data` không sinh FAQ. Không
có dữ liệu thì node chạy đúng mà demo vẫn không thấy gì.
