# Phân vai & Kế hoạch chi tiết — Phase 1

> Kế hoạch thực thi tới **GATE 2 (12/08)** và phần còn lại của Phase 1 (hạn 19/08).
> Scope & quyết định: [`PROJECT_CHARTER.md`](./PROJECT_CHARTER.md) · Kiến trúc: [`architecture_diagram.md`](./architecture_diagram.md)

**Lập ngày:** 07/08/2026 · **Còn 5 ngày tới GATE 2**

---

## 1. Phân vai

| Thành viên | Role | Sở hữu |
|---|---|---|
| **Nguyễn Trung Hiếu** | BE + Data | `src/api/`, `src/models/`, `src/services/checklist.py`, `alembic/`, thu thập và soạn nội dung KB, deploy Railway |
| **Nguyễn Việt Hải** | AI | `src/agents/`, `src/services/vectorstore.py`, `src/services/ingest.py`, prompt, chunking |
| **Nguyễn Minh Thu** | FE | `web/` |

**Quy tắc sở hữu:** mỗi thư mục có đúng một người sửa. Cần thay đổi file của người khác thì nhắn, đừng sửa thẳng — tránh conflict và tránh lặp lại chuyện tài liệu trôi lệch đã xảy ra ngày 07/08.

## 2. Nguyên tắc làm việc

1. **Contract trước, code sau.** Không ai bắt đầu code cho tới khi hợp đồng API và `ChatState` được viết ra và cả ba đồng ý. Đây là quy tắc ở charter mục 12, thêm vào chính vì hôm 07/08 đã dính một lần các tài liệu mâu thuẫn nhau.
2. **Bị chặn thì nói ngay**, đừng ngồi đợi. Cả ba đều có việc làm song song không phụ thuộc nhau — xem mục 3.
3. **Không commit secret.** Key Supabase và OpenAI chia sẻ qua kênh riêng, `.env` không lên git.
4. **Mỗi task có định nghĩa "xong" cụ thể** (cột DoD dưới đây). Chưa đạt DoD thì chưa qua task tiếp.
5. **Cập nhật `WORKLOG.md` cuối mỗi ngày** — đây là deliverable bị chấm, và mỗi người tự điền số giờ của mình.

## 3. Ai chặn ai

```
Hiếu: Supabase project + key ──┬──► Thu: đăng nhập thật
                               └──► Hiếu: migration, seed

Hiếu: data/kb/ (TT 05/2024 + web) ─► Hải: chunk + embed

Cả ba: chốt hợp đồng API + ChatState ──┬──► Thu: code UI theo contract
                                        └──► Hải: code node theo state

Hải: chat_graph xong ──────────────► Hiếu: route POST /chat
Hiếu: API thật xong ───────────────► Thu: bỏ mock, nối API
```

**Hai việc phải xong TRƯỚC MỌI THỨ (tối 07/08):**
- Hiếu tạo Supabase project và chia key — không có nó thì Thu không làm được gì
- Hiếu tải tài liệu KB — không có nó thì Hải không làm được gì

**Sau khi contract chốt, cả ba chạy song song hoàn toàn trong 2 ngày đầu.** Không ai phải đợi ai.

---

## 4. Ngày 0 — Tối 07/08 (2-3h)

| Ai | Việc | DoD |
|---|---|---|
| Hiếu | Tạo Supabase project; lấy `DATABASE_URL`, `SUPABASE_URL`, `ANON_KEY`, `SERVICE_KEY`, `JWT_SECRET`; chia cho Thu và Hải | Thu đăng nhập được vào Supabase dashboard |
| Hiếu | Cập nhật `src/config.py`: thêm biến Supabase, `chroma_persist_dir`, `rag_top_k`, LangSmith; đổi `database_url` mặc định khỏi SQLite | `get_settings()` đọc được `.env` mới |
| Hiếu | ~~Tải Thông tư~~ **Xong 08/08:** `data/kb/legal/` + `data/kb/web/`, chạy `scripts/fetch_legal_kb.py` và `scripts/scrape_kb.py` | Hải có file trong tay |
| **Cả ba** | **Họp 30 phút chốt hợp đồng API + `ChatState`**, ghi vào `docs/architecture_diagram.md` nếu có sửa | Ba người cùng xác nhận bằng văn bản |

> Nếu chỉ làm được một việc tối nay thì làm **Supabase project + chia key**. Nó chặn nhiều nhất.

---

## 5. Nguyễn Trung Hiếu — BE + Data

### 08/08 (T7) — Schema & dữ liệu

| Việc | File | DoD |
|---|---|---|
| Model SQLAlchemy: `USERS`, `CHECKLIST_ITEMS`, `CHECKLIST_COMPLETIONS`, `CHAT_HISTORY`, `DOCUMENTS`, `FAQ` | `src/models/db.py` | Import không lỗi |
| Alembic init + migration đầu tiên | `alembic/` | `alembic upgrade head` chạy sạch trên Supabase |
| **Soạn nội dung 12-15 checklist item thật** + script seed | `scripts/seed_checklist.py` | Query thấy đủ item, mỗi item có `conditions` và `item_type` hợp lệ |

**Nội dung checklist cần phủ đủ các nhánh** — đây là phần *dữ liệu*, không phải code, và là thứ quyết định demo có thuyết phục hay không:

| Nhóm | Ví dụ | `conditions` | `item_type` |
|---|---|---|---|
| Mọi cư dân | Ký nội quy toà nhà | `{}` | `bql_actionable` |
| Chỉ chủ hộ | Làm thẻ cư dân (CCCD + giấy tờ căn hộ) | `{"ownership_type":"owner"}` | `bql_actionable` |
| Chỉ người thuê | Làm thẻ cư dân (CCCD + hợp đồng thuê + uỷ quyền) | `{"ownership_type":"renter"}` | `bql_actionable` |
| Chỉ người thuê | Đăng ký tạm trú tại công an phường | `{"ownership_type":"renter"}` | **`third_party_info`** |
| Có xe | Đăng ký thẻ xe ô tô/máy | `{"has_car":true}` | `bql_actionable` |
| Theo tiện ích | Kích hoạt thẻ hồ bơi | `{"amenity_packages":"pool"}` | `bql_actionable` |

> ⚠️ Nhớ validate key của `conditions` phải khớp field thật của `USERS`. Gõ nhầm `ownership_typ` thì item **âm thầm không bao giờ hiện**, không báo lỗi gì.

### 09/08 (CN) — Rule engine & auth

| Việc | File | DoD |
|---|---|---|
| `matches()` + `generate_checklist()` | `src/services/checklist.py` | Hàm thuần, không import DB hay LangGraph |
| Test ma trận persona | `tests/test_services/test_checklist.py` | Mỗi tổ hợp `ownership_type × has_car × amenity_packages` ra đúng danh sách kỳ vọng; pytest xanh |
| Verify JWT Supabase | `src/api/deps.py` | Token hợp lệ trả về user; token sai trả 401 |

> ⏱ **Giới hạn 2h cho phần JWT.** Chưa xong thì chuyển sang `supabase-py` gọi `auth.get_user(jwt)` — chậm hơn một round-trip nhưng chắc chắn chạy, tối ưu sau. Đừng để việc này ăn hết một ngày.

### 10/08 (T2) — API cư dân

| Việc | File | DoD |
|---|---|---|
| `POST /onboarding`, `GET+PATCH /profile` | `src/api/routes/onboarding.py`, `profile.py` | Lưu và đọc lại đúng profile |
| `GET /checklist`, `PATCH /checklist/{id}` | `src/api/routes/checklist.py` | Trả item đã lọc + `item_type` + `progress_percent` |
| `POST /admin/users` (US-00) | `src/api/routes/admin.py` | Tạo được tài khoản cư dân qua Supabase admin API |

**Nhớ:** truy vấn dữ liệu cá nhân phải lọc theo `user_id` ngay trong câu query, không lấy hết rồi lọc sau (charter — ràng buộc bảo mật của đề bài).

### 11/08 (T3) — Tích hợp & deploy

| Việc | DoD |
|---|---|
| `POST /chat` — gọi `chat_graph` của Hải, ghi `CHAT_HISTORY` | Hỏi qua Swagger ra câu trả lời kèm `sources[]` |
| Deploy Railway + **gắn Volume** vào `chroma_persist_dir` | Redeploy xong embeddings vẫn còn |
| Tạo dữ liệu demo: 1 chủ hộ, 1 người thuê, 1 admin | Đăng nhập được cả ba |

### 12/08 (T4) — Dự phòng & demo

---

## 6. Nguyễn Việt Hải — AI

### 08/08 (T7) — Pipeline nạp tài liệu

| Việc | File | DoD |
|---|---|---|
| Chroma client, **tắt embedding function mặc định**, dùng `OpenAIEmbeddings` | `src/services/vectorstore.py` | Kết nối được, tạo collection `documents` |
| PDF → chunk → embed → Chroma kèm metadata | `src/services/ingest.py` | Metadata mỗi chunk có `document_id`, `title`, `source_type` |
| CLI nạp hàng loạt | `scripts/ingest_kb.py` | Nạp xong Thông tư, `collection.count() > 0` |

> ⚠️ **Cảnh báo quan trọng nhất của cả dự án:** nếu quên tắt embedding function mặc định của Chroma, lúc index sẽ dùng mô hình local còn lúc query dùng OpenAI. Vector khác không gian → retrieval trả về rác **mà không báo lỗi gì**. Chạy vẫn ra kết quả, chỉ là kết quả sai.

### 09/08 (CN) — Chất lượng truy xuất

| Việc | DoD |
|---|---|
| Soạn 10 câu hỏi thật cư dân hay hỏi, chạy retrieval, đối chiếu thủ công | **≥7/10 câu lấy về đúng đoạn có chứa câu trả lời** |
| Tinh chỉnh chunk size / overlap / cách cắt theo mục | Đạt ngưỡng trên rồi mới đi tiếp |

> Đây là **DoD quan trọng nhất của role AI**. Chunking hỏng là hỏng thầm lặng — code đúng hoàn toàn nhưng hệ thống trông như "AI kém". Không đạt 7/10 thì đừng viết node vội, quay lại chỉnh chunking.

### 10/08 (T2) — Dựng graph

| Việc | File | DoD |
|---|---|---|
| `ChatState` | `src/agents/state.py` | Đúng field đã chốt ở contract |
| Node truy xuất — search + **gộp `sources[]` theo `document_id`** | `src/agents/nodes/rag_retrieve.py` | Cùng tài liệu không xuất hiện 2 lần trong sources |
| Node sinh câu trả lời + **guard không có context** | `src/agents/nodes/generate.py` | Không có context thì **không gọi LLM**, trả câu từ chối |
| Dựng `chat_graph` | `src/agents/graph.py` | Chạy bằng script trực tiếp ra `answer` + `sources` |
| Xoá code mẫu của template | `nodes/example_node.py`, `tools/example_tool.py` | Đã xoá |

**Nhắc lại từ kiến trúc:** `sources[]` do node truy xuất sinh ra, **tuyệt đối không hỏi LLM tự liệt kê nguồn**. Đó là chỗ phần lớn hệ RAG thất bại.

### 11/08 (T3) — Test & quan sát

| Việc | DoD |
|---|---|
| Test graph với mock vectorstore + LLM | Test được: guard từ chối khi rỗng, sources gộp trùng đúng |
| Bật LangSmith (deliverable #4 của BTC) | Thấy trace trên dashboard |
| Bọc lời gọi Chroma trong `run_in_threadpool` | Không chẹn event loop |
| Hỗ trợ Hiếu nối graph vào route | `POST /chat` chạy được |

### 12/08 (T4) — Chuẩn bị câu hỏi demo

Chọn sẵn **2 câu**: một câu tài liệu trả lời được, một câu **ngoài tài liệu** để cho thấy hệ thống từ chối thay vì bịa. Câu thứ hai chính là điểm ăn điểm.

---

## 7. Nguyễn Minh Thu — FE

### 08/08 (T7) — Đăng nhập thật

| Việc | File | DoD |
|---|---|---|
| Supabase client + đăng nhập thật | `web/app/login/page.tsx` | Thay `<Link href="/dashboard">` tĩnh hiện tại bằng đăng nhập thật |
| Lưu session, gắn JWT vào header mọi request | `web/lib/` | Request có `Authorization: Bearer ...` |
| Chặn route khi chưa đăng nhập | | Chưa đăng nhập → về `/login` |

> Không làm trang đăng ký — tài khoản do BQL cấp (quyết định đã chốt ở charter).

### 09/08 (CN) — Form onboarding

| Việc | File | DoD |
|---|---|---|
| Trang `/onboarding` — 4 nhóm câu hỏi | `web/app/onboarding/page.tsx` | Submit được, có validate |

Bốn nhóm câu hỏi đúng theo schema đã chốt:
1. **Bạn là chủ hộ hay người thuê?** → `ownership_type` (owner / renter)
2. **Loại căn hộ** → `apartment_type`
3. **Bạn có xe không?** → `has_car` (boolean)
4. **Gói tiện ích đã đăng ký** → `amenity_packages` (**chọn nhiều**)

> Đây là trang **chưa tồn tại** và là mắt xích bắt buộc: không có form thì không có profile, không có profile thì checklist không lọc được gì. BE chưa xong thì dựng mock theo contract, nối API sau.

### 10/08 (T2) — Checklist thật

| Việc | DoD |
|---|---|
| `/checklist` dùng dữ liệu API thật | Hiển thị đúng item của từng persona |
| **Phân biệt `item_type`** | Mục `third_party_info` có nhãn rõ "quy trình ngoài BQL" |
| Tick hoàn thành + thanh % tiến độ | Tick xong reload vẫn giữ trạng thái |
| Chuyển hướng khi chưa onboarding | `onboarding_completed_at = null` → về `/onboarding` |

### 11/08 (T3) — Chat & deploy

| Việc | DoD |
|---|---|
| `/chat` gọi API thật | Hỏi ra câu trả lời |
| **Hiển thị nguồn trích dẫn** dưới câu trả lời | Thấy tên tài liệu, phân biệt tài liệu BQL và quy định công khai |
| `/profile` xem và sửa hồ sơ | Sửa xong checklist đổi theo |
| Deploy Vercel | URL công khai chạy được |

### 12/08 (T4) — Responsive & dự phòng

Giao diện cư dân ưu tiên điện thoại (chấm điểm UI/UX), giao diện BQL để desktop.

---

## 8. Kịch bản demo GATE 2

Viết ra để cả ba biết đích đến. Thứ tự này kể một câu chuyện liền mạch:

1. **BQL đăng nhập** → tạo tài khoản cho cư dân mới
2. **Cư dân đăng nhập lần đầu** → bị đưa thẳng tới form onboarding
3. **Điền form:** chủ hộ · căn 2PN · có xe · gói hồ bơi → checklist hiện ra
4. **Đăng nhập tài khoản thứ hai (người thuê)** → **checklist khác hẳn**: thêm giấy tờ hợp đồng thuê, có mục đăng ký tạm trú gắn nhãn "ngoài phạm vi BQL"
5. **Tick vài mục** → phần trăm tiến độ tăng
6. **Hỏi AI:** "Làm thẻ xe cần giấy tờ gì?" → trả lời **kèm nguồn trích dẫn**
7. **Hỏi câu ngoài tài liệu** → hệ thống **từ chối và hướng dẫn liên hệ BQL**, không bịa

> **Bước 4 và bước 7 là hai chỗ ăn điểm nhất.**
> Bước 4 chứng minh "cá nhân hóa theo tình huống từng hộ" — yêu cầu bắt buộc của đề bài.
> Bước 7 chứng minh ràng buộc "chính xác, không bịa thông tin" được xử lý bằng kỹ thuật chứ không phải bằng lời hứa trong prompt.
> Nếu thiếu thời gian, hy sinh thứ khác chứ đừng hy sinh hai bước này.

## 9. Điểm kiểm tra chung

| Thời điểm | Kiểm tra |
|---|---|
| Tối 08/08 | Ba người có chạy được phần của mình độc lập không? Ai bị chặn? |
| Tối 09/08 | Hải đã đạt 7/10 retrieval chưa? Hiếu đã có seed data chưa? — **hai thứ này trễ là demo hỏng** |
| Tối 10/08 | Thu đã gọi được API thật chưa? Nếu chưa, hôm sau ưu tiên nối API trước mọi thứ |
| Tối 11/08 | Chạy thử toàn bộ kịch bản demo trên URL đã deploy, không phải trên localhost |

## 10. Backlog W4 (13-19/08)

Vẫn thuộc Phase 1, đã hoãn có chủ đích khỏi GATE 2:

| Việc | Ai | Ghi chú |
|---|---|---|
| Nhánh FAQ + hiệu chỉnh ngưỡng | Hải | Cần ~20 câu hỏi thật để hiệu chỉnh |
| Giao diện BQL upload tài liệu | Hiếu + Thu | |
| CRUD FAQ cho BQL | Hiếu + Thu | |
| Dashboard BQL tối giản | Hiếu + Thu | Danh sách cư dân + % tiến độ |
| PWA: manifest + service worker + icon | Thu | Kiểm tra tài liệu Next.js trong `node_modules/next/dist/docs/` trước khi code — bản trong repo có breaking change |
| **Nạp toàn bộ KB thật — hạn 17/08** | Hiếu (soạn) + Hải (nạp) | **Mốc này không được trễ** |
| Cổng quyết định nguồn dữ liệu — 13/08 | Cả nhóm | ≥3 bộ tài liệu thật → dùng nguồn thật; 1-2 bộ → làm khung; không có → dùng hẳn phương án dự phòng |
