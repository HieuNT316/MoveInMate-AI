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

## 7b. Kế hoạch sửa đổi — tối 11/08, đêm trước GATE 2

Mục 5-7 ở trên viết ngày 07/08 và **đã lạc hậu**. Thực tế tới 11/08: RAG đã xong (AI), DB + API + đăng nhập tạm đã xong (BE), dữ liệu quy trình BQL đã sinh (BE). Còn lại đúng một đêm.

### Ba việc bắt buộc, theo thứ tự chặn nhau

| # | Việc | Ai | Ước | Vì sao xếp trước |
|---|---|---|---|---|
| 1 | **FE hiển thị `suggested_action`** — khai `SuggestedAction` type + hiện nút trong bong bóng chat + `/checklist?item=<id>` cuộn tới đúng mục | Thu | ~45' | **BE đã trả field này từ 10/08 nhưng FE không khai type nên bỏ qua hoàn toàn.** Không có bước này thì agent điều hướng vô hình, không demo được gì |
| 2 | **BE đối chiếu tất định** — chạy `_match_checklist_item` trên mọi câu hỏi, tool LLM hạ thành tín hiệu bổ trợ | Hiếu + **Hải duyệt** | ~45' | Tool mới bắn 2/4 cách hỏi. **Phải hỏi Hải trước**: docstring tool cố ý không bắn cho câu hỏi thuần thông tin, sửa ẩu là phá thiết kế của anh ấy |
| 3 | **Tổng duyệt demo trên URL đã deploy** + phương án dự phòng | Cả ba | ~1h | Mục 9 đã yêu cầu từ đầu, chưa làm |

**Backend đã deploy 11/08:** `https://moveinmate-api-production.up.railway.app`

Deploy bằng **Railway CLI**, không qua GitHub: repo là private thuộc org, mà Hiếu chỉ có quyền `push` (`admin=false`) nên không cài được Railway GitHub App — việc đó cần owner org. Hệ quả: **không tự deploy khi push**, mỗi lần cập nhật phải chạy lại `railway up` từ PowerShell (Git Bash dùng đường dẫn `/d/...` nên CLI không nhận ra liên kết).

Biến môi trường đẩy bằng `python -m scripts.railway_env` (đọc từ `.env`, truyền qua stdin nên secret không vào lịch sử shell).

### Đã loại khỏi tối nay — và lý do

| Việc | Vì sao loại |
|---|---|
| **`APPLICATIONS` + form nộp hồ sơ online** | `architecture_diagram.md` mục 4.4 ghi rõ *"chỉ chuẩn bị tín hiệu, không kéo Phase 2 lên sớm"*. Thêm bảng DB + endpoint + form trong đêm cuối, **chưa có contract viết ra** giữa FE và BE, là vi phạm chính mục 12 Governance. Đích tạm `/checklist?item=<id>` đủ kể chuyện cho GATE 2 |
| Ba mục UX của mentor (mang gì/bao lâu/ở đâu, huy hiệu, chat có cấu trúc) | Mentor góp ý cho sản phẩm, không ra hạn GATE 2. Dữ liệu đã sẵn trong `data/kb/bql/`, làm ở W4 rẻ hơn nhiều |
| Đổi nguồn embedding sang OpenAI | Bắt buộc ingest lại + hiệu chỉnh lại ngưỡng. Không đụng trước demo |
| Vặn `rag_max_distance` | Hai cụm cách nhau ~0.04, hiệu chỉnh mới trên 4 câu. Sửa mù = đánh bạc |

### Việc chưa xong mà kế hoạch cũ coi là bắt buộc

**US-01 Auth qua Supabase vẫn chưa làm** (~12h ước tính ban đầu). Đăng nhập hiện tra theo email, không kiểm mật khẩu. Đây là hạng mục `[GATE 2]` trong charter mục 4 — cần **quyết định rõ ràng của nhóm trưởng**, không để trôi:

- **Hoãn có công bố:** nói thẳng với mentor ở GATE 2 rằng auth là hạng mục còn nợ, hạn W4. Đây là lựa chọn nhóm đã nghiêng về từ 08/08 (giữ RAG, hy sinh auth).
- **Hoặc** làm tối nay, chấp nhận bỏ việc 1-3 ở trên.

Không chọn = mặc định rơi vào phương án đầu nhưng không ai nói với mentor, và đó là cách tệ nhất.

### Deliverable BTC còn nợ

`eval/results/report.md` vẫn rỗng. Retrieval accuracy chưa đo trên bộ đủ lớn (ngưỡng hiện hiệu chỉnh trên 4 câu). Không kịp trước GATE 2 — xếp ngay sau, trước mốc 17/08.

## 8. Kịch bản demo GATE 2

Viết ra để cả ba biết đích đến. Thứ tự này kể một câu chuyện liền mạch:

1. **BQL đăng nhập** → tạo tài khoản cho cư dân mới
2. **Cư dân đăng nhập lần đầu** → bị đưa thẳng tới form onboarding
3. **Điền form:** chủ hộ · căn 2PN · có xe · gói hồ bơi → checklist hiện ra
4. **Đăng nhập tài khoản thứ hai (người thuê)** → **checklist khác hẳn**: thêm giấy tờ hợp đồng thuê, có mục đăng ký tạm trú gắn nhãn "ngoài phạm vi BQL"
5. **Tick vài mục** → phần trăm tiến độ tăng
6. **Hỏi AI:** "Làm thẻ xe cần giấy tờ gì?" → trả lời **kèm nguồn trích dẫn**
7. **Hỏi câu ngoài tài liệu** → hệ thống **từ chối và hướng dẫn liên hệ BQL**, không bịa
8. **(Thêm 11/08) Hỏi "ai xử lý hồ sơ thẻ xe của tôi?"** → trả lời đúng bộ phận An ninh, nơi nộp, thời hạn, 5 bước xử lý — **đây là phần agent điều hướng mentor muốn thấy**
9. **(Thêm 11/08, chỉ khi việc 1-2 mục 7b xong)** "Dẫn tôi đến chỗ nộp hồ sơ đăng ký thẻ xe" → hiện nút điều hướng, bấm vào nhảy sang đúng mục trong checklist

> **Câu phải nói trong lời dẫn:** phần thủ tục nội bộ dùng **dữ liệu mô phỏng** có gắn nhãn; phần quy định pháp luật là văn bản thật (Quy chế kèm TT 05/2024/TT-BXD). Nói trước là minh bạch, bị hỏi mới nói là bị bắt lỗi.

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

## 11. Vận hành — bổ sung sau rà soát 11/08

Rà soát hệ thống với góc nhìn sản phẩm chạy thật cho thấy **8 thành phần vận hành
còn thiếu**. Chi tiết và lý do: [`OPERATIONS.md`](./OPERATIONS.md). Dưới đây là
phân công.

### Làm sớm — trước hoặc ngay sau GATE 2

| # | Việc | Ai | Ước | Vì sao gấp |
|---|---|---|---|---|
| V1 | **Bật LangSmith tracing** — tạo tài khoản, đặt `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` ở `.env` và trên Railway, xác minh trace hiện ra | **Hải** | 30' | Đang được khai là deliverable #4 của BTC ở 4 nơi trong tài liệu mà `src/` không có gì. Mentor hỏi "cho xem trace" là không có gì để mở |
| V2 | **Giới hạn tần suất** `slowapi` — 20 lượt/phút/người cho `/chat`, 100 cho endpoint đọc | **Hiếu** | 1h | URL công khai, mỗi lượt chat tốn tiền thật trên key trả phí; hạn mức Google cạn là mất luôn khả năng demo |
| V3 | **Sửa hiển thị khi guard trượt** — `generate` nhận ra câu trả lời mang nghĩa từ chối thì đổi `answer_source` thành `no_context` và bỏ `sources` | **Hải** | 1h | Đo được 0/3 ở nhóm "đúng lĩnh vực nhưng KB không có": hiện trích dẫn dưới câu "tôi không biết" là kiểu hiển thị gây hiểu nhầm nhất |

### W4 (13-19/08)

| # | Việc | Ai | Ước |
|---|---|---|---|
| V4 | **`/health/deep`** kiểm DB + Chroma + `collection.count()`, trả 503 khi có thành phần chết. Giữ `/health` nông cho Railway probe | Hiếu | 1h |
| V5 | **Log có cấu trúc** thay `print()` — có mức, mốc thời gian, `request_id` xuyên suốt một request | Hiếu | 2h |
| V6 | **Ghi token và chi phí** mỗi lượt chat vào `chat_history` (thêm cột), để đặt được ngân sách và phát hiện lượt bất thường | Hiếu + Hải | 2h |
| V7 | **Nút 👍/👎** dưới mỗi câu trả lời, lưu vào DB | Thu + Hiếu | 2h |
| V8 | **Che PII** (số CCCD, số điện thoại) trước khi ghi `chat_history` | Hiếu | 1h |
| V9 | **Bắt lỗi tập trung** — exception handler trả lỗi có cấu trúc và ghi log đầy đủ | Hiếu | 1h |
| V10 | **Chạy lại `run_eval` sau mỗi lần đổi KB hoặc ngưỡng**, lưu kết quả vào `eval/results/` | Hải | mỗi lần 10' |

### Ai gánh gì

- **Hiếu (BE):** V2, V4, V5, V6, V8, V9 — hạ tầng vận hành
- **Hải (AI):** V1, V3, V6, V10 — quan sát và chất lượng mô hình
- **Thu (FE):** V7 — thu thập phản hồi người dùng

V1, V2, V3 nên xong trước khi công bố URL rộng rãi. V10 là thói quen, không phải
việc một lần: **đổi KB hoặc đổi ngưỡng mà không đo lại thì không biết mình vừa
làm tốt lên hay tệ đi.**


---

## 12. Kế hoạch 15/08 — ngày demo GATE 2

> **Cách dùng:** tự tick `[x]` việc của mình và ghi ngày. Ai đổi trạng thái thì
> commit luôn file này để hai người kia thấy — đừng báo miệng rồi quên.
>
> Lập sau rà soát sáng 15/08. Thay thế các mốc "trước thứ Bảy" ở mục 11.

### Đang ở đâu

| | Trạng thái |
|---|---|
| Backend Railway | Multi-turn + US-13 nộp hồ sơ — **đã chạy, kiểm chứng bằng JWT thật** |
| Frontend Vercel | **Đi sau `main` ba lớp**: redesign dashboard BQL, lịch sử chat, multi-turn |
| Eval | 32/35 · 91% — **đo trước khi có multi-turn**, chưa đo lại |
| Test | 111 pass · coverage 84% |
| CI | Đỏ ở mọi nhánh vì tài khoản tổ chức vướng thanh toán, không phải lỗi code |

### Trước demo — chỉ ba việc, xếp theo thứ tự chặn nhau

Hôm nay là ngày demo. **Nguyên tắc: không thêm tính năng mới vào nhánh sẽ demo.**
Đổi code vài giờ trước khi trình bày là cách hỏng demo phổ biến nhất.

| | Việc | Ai | Ước | Xong |
|---|---|---|---|---|
| A1 | **Deploy lại Vercel.** Không có bước này thì toàn bộ việc của cả nhóm ba ngày qua không ai nhìn thấy. `git checkout main && git pull`, rồi `cd web && vercel --prod` | **Thu** | 15' | [ ] |
| A2 | **Sửa tên cache service worker.** `moveinmate-shell-v1` cố định + chiến lược cache-first ⇒ ai đã từng mở trang sẽ **vẫn thấy bản cũ sau A1**, kể cả Ctrl+F5. Cho tên cache đổi theo mỗi lần build; phần dọn cache cũ đã viết sẵn ở `activate` | **Thu** | 20' | [ ] |
| A3 | **Chạy lại `python -m scripts.run_eval`.** Con số 32/35 đang dùng trong báo cáo đo trên kiến trúc **trước** `rewrite_query`. Báo cáo số cũ cho kiến trúc mới là sai. Tốn 35 lượt embedding nên để đúng vai AI chạy | **Hải** | 30' | [ ] |

Nếu A1/A2 chưa xong thì demo bằng **tab ẩn danh** và nói rõ đang chạy bản nào.

### Sau demo — theo thứ tự ưu tiên

| | Việc | Ai | Ước | Xong |
|---|---|---|---|---|
| B1 | **Upload ảnh minh chứng (US-13 phần còn lại).** Bảng `attachments`, bucket Supabase Storage **private**, `POST/GET /applications/{id}/attachments`. Thêm `kind` phân biệt hai loại hồ sơ (xem dưới) | Hiếu | 3h | [ ] |
| B2 | Form nộp hồ sơ + hiện "Bộ phận · Nơi nộp · Thời hạn" trong checklist. Hợp đồng đã chốt ở [`CONTRACT_US13.md`](./CONTRACT_US13.md), mock được ngay | Thu | 1h15 | [ ] |
| B3 | Giao diện upload ảnh minh chứng cho thủ tục ngoài phạm vi BQL | Thu | 1h | [ ] |
| B4 | Trang theo dõi trạng thái hồ sơ + nút BQL đổi trạng thái | Thu | 1h | [ ] |
| B5 | **V3 — sửa hiển thị khi guard trượt.** Vẫn là lỗi nguy hiểm nhất còn lại: 3 câu "đúng lĩnh vực nhưng KB không có" hiện trích dẫn ngay dưới câu "tôi không biết" | **Hải** | 1h | [ ] |
| B6 | Cập nhật charter + `architecture_diagram.md` + README + `.env.example`. Hiện charter vẫn ghi `APPLICATIONS` là Phase 2 trong khi nó đã chạy thật | Hiếu | 45' | [ ] |
| B7 | **V2 — rate limiting.** Cố tình để sau demo: đặt ngưỡng sai là chặn nhầm đúng lúc đang trình bày | Hiếu | 1h | [ ] |
| B8 | **V1 — LangSmith.** Khai là deliverable ở 4 nơi trong tài liệu, `src/` không có dòng nào | **Hải** | 30' | [ ] |
| B9 | Partial unique index chống nộp trùng hồ sơ (hiện chỉ chặn ở tầng ứng dụng, hai request đồng thời lọt cả hai) | Hiếu | 20' | [ ] |
| B10 | Video Demo · Pitch Deck — hai deliverable BTC còn nợ | Cả nhóm | — | [ ] |

### Ranh giới phải giữ khi làm B1 — đọc trước khi code

**Nộp hồ sơ và nộp minh chứng là hai việc khác bản chất.** Gộp chung là phá đúng
cái bất biến mà cả sản phẩm đang dựa vào.

| | Nộp hồ sơ (`bql_processing`) | Nộp minh chứng (`self_declared`) |
|---|---|---|
| Ví dụ | Đăng ký thẻ xe, thẻ cư dân | Đăng ký tạm trú, cập nhật cư trú |
| Ai xử lý | Bộ phận BQL | Không ai — cư dân tự khai |
| Định tuyến | Có bộ phận | Không có bộ phận nào |
| BQL làm gì | Tiếp nhận → xử lý → trả kết quả | Chỉ **ghi nhận**, hoặc báo cần bổ sung |
| File | Tuỳ chọn | **Bắt buộc** — đây chính là nội dung nộp |

Giao diện tuyệt đối không hiện "Ban quản lý đang xử lý hồ sơ tạm trú của bạn" —
sai sự thật, và phá nguyên tắc "BQL không mạo nhận quy trình của cơ quan khác".

**Dữ liệu cá nhân.** `architecture_diagram.md` mục cuối có quy tắc: không bao giờ
đưa dữ liệu cá nhân cư dân vào vector store — Chroma không phân quyền, đã index
là ai hỏi đúng câu cũng lấy được. Ảnh CCCD/VNeID là giấy tờ tuỳ thân:

- Bucket **private**, đọc qua signed URL hết hạn ngắn — không bao giờ URL công khai
- **Tuyệt đối không** embed vào Chroma
- Chỉ chủ hồ sơ và BQL đọc được
- Giới hạn 5MB, chỉ nhận `jpeg` / `png` / `pdf`, tên file lưu bằng UUID
- **Demo dùng ảnh giả hoặc đã che số** — đừng dùng CCCD thật của ai trong nhóm

**Cách nối API không phá hợp đồng đang code:** giữ nguyên `POST /applications`
dạng JSON, thêm `POST /applications/{id}/attachments` dạng multipart. Tạo hồ sơ
trước rồi đính file — thuần cộng thêm, không sửa cái đã chốt với Thu.

### Nhắc lại hai điều đã trả giá

**Charter mục 12 — chốt hợp đồng bằng văn bản trước khi hai vai code song song.**
Ngày 12/08 Hiếu sửa `web/app/chat/page.tsx` để hiện nút điều hướng mà không báo;
Thu tự viết bản khác. Cả hai chạy được, nhưng một bản thành code chết trên `main`.

**Đừng bấm nút "Đổi" ở trang Hồ sơ trên bản deploy khi đang thử.** Nó sửa dữ liệu
thật và làm lệch persona demo. Đã phải vá tay hai lần.
