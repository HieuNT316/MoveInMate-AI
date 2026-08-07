# PROJECT CHARTER — MoveInMate

> Tài liệu chính thức, là nguồn sự thật (single source of truth) cho scope, kiến trúc và quyết định của dự án.
> Kiến trúc kỹ thuật chi tiết: [`ARCHITECTURE.md`](./ARCHITECTURE.md).
>
> *(Bản tóm tắt bối cảnh cũ `MoveInMate_Context_Summary.md` đã được gỡ bỏ ngày 06/08 — nội dung của nó đã được chuẩn hoá và thay thế hoàn toàn bởi tài liệu này. Cần tra lịch sử thì xem git.)*

**Cập nhật lần cuối:** 06/08/2026
**Team:** P-225 — AI20K Build Phase, Cohort 3

---

## 1. Problem Statement & Định vị sản phẩm

### Đề bài gốc (BTC, nguyên văn — nguồn thẩm quyền cao nhất)

> **Thực trạng:** Cư dân mới nhận nhà ở Doanh nghiệp bất động sản X phải tự mò hàng loạt thủ tục: đăng ký thẻ cư dân, thẻ xe, internet, nội quy, kích hoạt tiện ích, gây choáng ngợp và sót việc.
>
> **Vấn đề:** Cần AI Agent dẫn dắt onboarding **cá nhân hóa**, lập checklist thủ tục **theo tình huống từng hộ**, hướng dẫn từng bước, tự tạo yêu cầu tới đúng bộ phận và theo dõi tiến độ hoàn tất.
>
> **Ràng buộc:** HITL cho các thủ tục cần BQL xác nhận hồ sơ/giấy tờ; bảo mật giấy tờ & thông tin cá nhân cư dân mới; chính xác trong hướng dẫn thủ tục theo từng khu; tối ưu chi phí & trải nghiệm nhiều bước.
>
> **Yêu cầu đầu ra — Cơ bản:** App deploy, đăng nhập; agent tạo checklist onboarding cá nhân hóa, hướng dẫn từng bước có trích tài liệu, theo dõi tiến độ (memory).
>
> **Yêu cầu đầu ra — Nâng cao:** Agent tự tạo & định tuyến yêu cầu tới các bộ phận, nhắc việc còn thiếu, HITL BQL duyệt hồ sơ, dashboard tiến độ onboarding & eval tỉ lệ hoàn tất thủ tục.

**⚠️ Quan trọng:** "Cá nhân hóa" và "theo tình huống từng hộ" xuất hiện ở cả phần Vấn đề lẫn Yêu cầu Cơ bản — đây là **yêu cầu chấm điểm bắt buộc của đề bài**, không phải lựa chọn kiến trúc của nhóm. Bỏ cá nhân hóa = không đáp ứng đúng đề tài, không phải vấn đề chất lượng thực thi. (Xác nhận 06/08, xem mục 7.)

**Vấn đề (diễn giải theo bối cảnh Vinhomes):** Cư dân mới tại chung cư Vinhomes phải tự xoay xở với thủ tục onboarding (thẻ cư dân, thẻ xe, tiện ích...) mà không có hướng dẫn hệ thống hóa. Các thủ tục này hiện do phòng ban xử lý thủ công, chưa có giải pháp phần mềm/agent nào.

**Định vị so với Vinhomes Resident app:** App hiện có chỉ xử lý đặt tiện ích, thanh toán phí, gửi phản ánh — phục vụ cư dân *đã ổn định*. Hồ sơ giấy tờ và thẻ ra/vào vẫn phải làm việc trực tiếp qua BQL. MoveInMate lấp khoảng trống này — phục vụ **4-6 tuần đầu tiên** khi cư dân chưa biết mình cần làm gì, với điểm khác biệt cốt lõi là **checklist cá nhân hóa theo hồ sơ cư dân** (không phải danh sách chung chung).

**Persona (xác nhận 06/08, chốt sau họp team):** **Chủ căn hộ là persona chính**, có thêm **nhánh cho người thuê**. Buyer thật là **BQL** (mục 3), nên ưu tiên đúng đối tượng BQL quản lý trực tiếp là chủ hộ; người thuê vẫn được phục vụ nhưng qua nhánh riêng. Cơ sở cá nhân hóa: `ownership_type` (owner/renter) xác định nhánh + giấy tờ khác nhau cho các thủ tục **thuộc phạm vi BQL**; loại căn hộ/có xe/gói tiện ích (theo PRD) xác định các bước tiện ích cụ thể. Chi tiết cơ chế: xem mục 6 và mục 7.

**Phạm vi quy trình (xác nhận 06/08):** App chỉ xử lý đầy đủ (tracking, HITL, trích nguồn từ tài liệu nội bộ) các thủ tục **thuộc phạm vi BQL** (thẻ cư dân, thẻ xe, tiện ích...). Các thủ tục thuộc bên thứ ba (vd. tạm trú/lưu trú qua công an) **chỉ đưa hướng dẫn tham khảo theo quy định chung công khai hiện hành**, không tracking/HITL, nguồn trích dẫn ghi rõ là quy định pháp luật công khai (không phải tài liệu nội bộ BQL) để tránh vi phạm NFR "tránh bịa thông tin". Cơ chế: field `item_type` trên `CHECKLIST_ITEMS` (mục 6).

**Scope địa lý (xác nhận 06/08):** **Vinhomes Smart City** — 1 khu cụ thể, không multi-khu. Câu "chính xác theo từng khu" trong đề bài hiểu là đảm bảo thông tin đúng với khu được chọn.

## 2. Mục tiêu & Success Criteria

| Mốc | Tiêu chí "xong" |
|---|---|
| GATE 2 (12/08) | Form onboarding (chủ hộ + nhánh người thuê) → checklist cá nhân hóa theo `ownership_type`/loại căn/xe/tiện ích → tiến độ → hỏi đáp AI → Dashboard BQL tối giản, chạy end-to-end, dù KB có thể còn placeholder |
| W4 kết thúc (19/08) | Toàn bộ Phase 1 chạy với dữ liệu thật, không còn mock |
| Demo Day (01/09) | ≥35/50 điểm theo tiêu chí BTC (Product ≥8, System ≥7, UI/UX ≥7, DevOps ≥6, Code ≥7) |

## 3. Stakeholders & Roles

**Phân role (xác nhận 06/08, quyết định của nhóm trưởng):** chia theo **AI / FE / BE**. Phần **dữ liệu (KB, thu thập tài liệu) là việc chung cả team**, không thuộc riêng role nào.

| Role | Việc chính |
|---|---|
| AI | Pipeline RAG, LangGraph, prompt, FAQ fallback logic, eval chất lượng trả lời |
| BE | FastAPI, schema DB, rule engine checklist, Supabase Auth, deploy Railway |
| FE | UI Next.js (`web/`) — hiện có dashboard/login/profile/checklist/chat dạng mock; cần thêm form onboarding |
| Cả team | Thu thập dữ liệu KB thật (cổng 13/08), test/QA |
| Mentor (Đặng Hải Lộc) | Tư vấn, đầu mối giới thiệu BQL (nếu có) |
| BTC (AI20K Cohort 3) | Chấm điểm, cung cấp `AI_LOG_API_KEY`, hạ tầng logging |

> ⚠️ **Lưu ý rủi ro đã nêu khi phân tích phương án role (06/08):** mô hình AI/FE/BE có 2 điểm cần bù đắp có chủ đích: (1) dữ liệu KB là "việc của chung" — cần phân công task cụ thể theo tuần trong WORKLOG.md, tránh không ai làm; (2) ranh giới BE (schema/rule engine) và AI (LangGraph state) giao nhau — 2 người phải thống nhất contract trước khi code (mục 12).

**Khách hàng sản phẩm (business, xác nhận 06/08):** Buyer = **BQL** (đơn vị trả tiền/triển khai). Cư dân là end-user, được BQL phân bổ/cấp quyền truy cập app — không phải người ra quyết định mua hay trả phí. Mọi ưu tiên tính năng nên phục vụ đúng nhu cầu BQL (giảm tải trả lời lặp lại, theo dõi tiến độ cư dân) trước, cư dân là người thụ hưởng gián tiếp.

## 4. Scope

### Phase 1 — Lõi

**Chia hai lát cắt (quyết định 06/08):** tổng effort Phase 1 ~120h, chia 3 người trong 6 ngày tới GATE 2 là ~6,7h/người/ngày không nghỉ — không thực tế. Nên phần bắt buộc cho 12/08 được cắt gọn lại, phần còn lại vẫn thuộc Phase 1 nhưng làm ở W4 (hạn 19/08).

**Lát cắt `[GATE 2]` — bắt buộc xong 12/08:**

| ID | Tính năng | Effort |
|---|---|---|
| US-00 (mới, 06/08) | BQL tạo/cấp tài khoản cư dân (không tự đăng ký) | ~4h |
| US-01 | Auth qua Supabase Auth (đăng nhập bằng tài khoản BQL cấp) | 12h |
| US-02 | Form onboarding + rule-based profiling (không LLM) — thuộc tính: `ownership_type`, loại căn, có xe, gói tiện ích | 8h |
| US-03/US-04 | Checklist cá nhân hóa (lọc trực tiếp) + tiến độ | 20h + 12h |
| US-05 (một phần) | **RAG** hỏi đáp có trích nguồn — chưa có nhánh FAQ | ~30h |
| US-06/US-07 | Xem/sửa hồ sơ, lịch sử chat | ~6h |
| — | Nạp KB bằng script CLI (chưa cần giao diện upload) | ~4h |

**Lát cắt `[W4]` — vẫn Phase 1, hạn 19/08:**

| ID | Tính năng | Effort | Ghi chú |
|---|---|---|---|
| US-05 (phần còn lại) | Nhánh FAQ + hiệu chỉnh ngưỡng | ~10h | Chi phí thật ở hiệu chỉnh, cần dữ liệu thật |
| US-08 | Giao diện BQL upload tài liệu | ~8h | |
| US-09 | CRUD FAQ cho BQL | ~6h | |
| US-12-mini | Dashboard BQL tối giản (danh sách + % tiến độ) | ~5h | |
| — | PWA: manifest + service worker + icon | ~5h | |

### Phase 2 — Nâng cao (W4-W5, không cắt, chỉ hoãn)

| ID | Tính năng | Effort | Ghi chú |
|---|---|---|---|
| US-10 | Duyệt hồ sơ/giấy tờ (APPLICATIONS: CCCD, hợp đồng, thanh toán) | 12h | **Đã xác nhận giữ Phase 2** — không vào GATE 2 |
| US-11 | Agent tạo ticket khi RAG không đủ tự tin | 14h | Lý do LangGraph tồn tại trong kiến trúc |
| US-12 | Dashboard BQL nâng cao (biểu đồ, bộ lọc) — nối tiếp bản mini ở Phase 1 | 13h | Effort gốc 18h, trừ 5h đã làm bản mini ở Phase 1 |
| US-13 | Định tuyến đa phòng ban | 10h | |
| US-14 | Nhắc việc còn thiếu (in-app) | 8h | Không email/SMS |
| US-15 | Eval tỷ lệ hoàn tất | 6h | Làm offline, đưa số liệu vào slide |

### Loại hoàn toàn khỏi scope
Đa ngôn ngữ, OCR xác thực giấy tờ, thông báo email/SMS/Zalo, analytics nâng cao.

## 5. User Stories & Use Cases

### Phase 1

| ID | Actor | Muốn | Để |
|---|---|---|---|
| US-00 | BQL | Tạo/cấp tài khoản cho cư dân | Cư dân có thể đăng nhập — *mới, hệ quả của quyết định "không tự đăng ký" (06/08)* |
| US-01 | Cư dân | Đăng nhập bằng tài khoản do BQL cấp (Supabase Auth) | Dùng hệ thống |
| US-02 | Cư dân | **Điền form onboarding** (ownership_type, loại căn hộ, có xe, gói tiện ích) | Hệ thống tạo checklist cá nhân hóa — *là mắt xích bắt buộc để US-04 hoạt động* |
| US-03 | Cư dân | Xem Dashboard | Tổng quan chức năng + trạng thái hồ sơ |
| US-04 | Cư dân | Xem Checklist cá nhân hóa & tick hoàn thành | Theo dõi tiến độ nhận nhà |
| US-05 | Cư dân | Hỏi AI (FAQ fallback → RAG có trích nguồn) | Giải đáp thủ tục nhận nhà |
| US-06 | Cư dân | Xem **và sửa** hồ sơ | Kiểm tra/cập nhật thông tin cá nhân, căn hộ, persona — sửa xong checklist tự cập nhật (xác nhận 06/08) |
| US-07 | Cư dân | Xem lịch sử chat | Tra cứu lại hội thoại |
| US-08 | BQL | Upload tài liệu | Cung cấp nguồn cho RAG |
| US-09 | BQL | Quản lý FAQ | Fallback nhanh trước khi gọi RAG |

### Phase 2

| ID | Actor | Muốn | Để |
|---|---|---|---|
| US-10 | BQL | Duyệt hồ sơ/giấy tờ cư dân | Kiểm tra CCCD/hợp đồng, cập nhật Pending/Approved/Need More Info/Rejected |
| US-11 | Agent | Tạo ticket khi không đủ tự tin trả lời | Chuyển cho BQL xử lý |
| US-12 | BQL | Dashboard tổng quan | Theo dõi cư dân/hồ sơ |
| US-13 | Agent | Định tuyến đúng phòng ban | Ticket tới đúng nơi xử lý |
| US-14 | Cư dân | Nhận nhắc việc còn thiếu | Không bỏ sót thủ tục |

### Use Cases tương ứng
UC00 BQL tạo/cấp tài khoản cư dân · UC01 Đăng nhập · UC02 Điền form onboarding · UC03 Xem Dashboard · UC04 Xem Checklist & tiến độ · UC05 Đánh dấu hoàn thành Checklist · UC06 Xem hồ sơ · UC07 Xem lịch sử chat · UC08 Hỏi AI (FAQ → RAG) · UC09 Upload tài liệu (BQL) · UC10 Quản lý FAQ (BQL) · UC11 Duyệt hồ sơ (BQL, Phase 2)

## 6. Data Model (đã sửa để khớp quyết định cá nhân hóa + Supabase Auth)

### USERS
| Field | Type | Ghi chú |
|---|---|---|
| user_id | INT, PK | |
| auth_user_id | UUID, FK → Supabase `auth.users.id` | **Nguồn xác thực duy nhất — không tự lưu password** |
| full_name, email, phone | VARCHAR | |
| apartment, building | VARCHAR | |
| role | ENUM(resident, admin) | |
| ownership_type | ENUM(owner, renter), nullable | Null cho tới khi hoàn thành onboarding. Chọn nhánh chủ hộ/người thuê |
| apartment_type | VARCHAR, nullable | Loại căn hộ (theo PRD) — giá trị cụ thể chốt khi có dữ liệu Smart City thật |
| has_car | BOOLEAN | |
| amenity_packages | JSONB (array), nullable | Gói tiện ích đã đăng ký, multi-select — vd `["pool", "gym"]` |
| onboarding_completed_at | TIMESTAMP, nullable | |
| created_at, updated_at | TIMESTAMP | |

*Đã bỏ so với bản trước (06/08): `has_pet`, `nationality`, `has_power_of_attorney`, `household_size` — không nằm trong bộ thuộc tính đã chốt (ownership_type + loại căn/xe/gói tiện ích theo PRD). Thêm lại khi có bằng chứng thủ tục thật cần tới.*

### CHECKLIST_ITEMS (bảng template — team seed nội dung chung)
| Field | Type | Ghi chú |
|---|---|---|
| checklist_item_id | INT, PK | |
| task_name | VARCHAR | |
| description | TEXT, nullable | |
| category | VARCHAR, nullable | |
| item_type | ENUM(bql_actionable, third_party_info) | **Mới (06/08):** `bql_actionable` = thủ tục BQL xử lý, có tracking/HITL/trích nguồn nội bộ; `third_party_info` = quy trình bên thứ ba (tạm trú/công an...), chỉ hướng dẫn tham khảo theo quy định công khai, cư dân tự tick, không HITL |
| conditions | JSONB | `{}` = áp dụng mọi người; vd `{"ownership_type":"renter"}`. Với `amenity_packages` (multi-select): value đơn được hiểu là "nằm trong danh sách", vd `{"amenity_packages":"pool"}` khớp user có pool trong gói. **Validate key phải khớp field hợp lệ của USERS khi seed** (chặn lỗi gõ nhầm) |
| order_index | INT | |

### CHECKLIST_COMPLETIONS (đổi tên + đổi thiết kế 06/08 — chỉ lưu mục ĐÃ hoàn thành)
| Field | Type | Ghi chú |
|---|---|---|
| completion_id | INT, PK | |
| user_id | FK → USERS | |
| checklist_item_id | FK → CHECKLIST_ITEMS | |
| completed_at | DATETIME | Có dòng = đã xong; không có dòng = chưa xong |
| | UNIQUE(user_id, checklist_item_id) | |

**Lọc trực tiếp, không chốt cứng checklist lúc onboarding.** Danh sách hiển thị được tính lại mỗi lần `GET /checklist`: lọc `CHECKLIST_ITEMS` theo profile hiện tại → left join bảng này. Lý do đổi (06/08): (a) BQL cập nhật thủ tục thì cư dân cũ thấy ngay, không cần logic đồng bộ; (b) cư dân sửa hồ sơ thì checklist tự cập nhật, không cần logic gộp dễ mất dữ liệu; (c) không phát sinh câu hỏi khó "mục đã tick nhưng không còn khớp điều kiện thì xử lý sao".

Tiến độ (%) = số dòng completion / tổng số item khớp `conditions` của user đó — tính tại query time, không cần bảng PROGRESS riêng.

### CHAT_HISTORY (bổ sung field trích nguồn — yêu cầu cốt lõi của US-05)
| Field | Type | Ghi chú |
|---|---|---|
| chat_id | INT, PK | |
| user_id | FK → USERS | |
| question, answer | TEXT | |
| source_type | ENUM(faq, rag) | Biết câu trả lời từ FAQ hay RAG |
| sources | JSONB, nullable | `[{document_id, title, snippet}]` — **bổ sung: bản gốc thiếu field này dù US-05 yêu cầu "trích nguồn"** |
| created_at | DATETIME | |

### FAQ
| Field | Type |
|---|---|
| faq_id | INT, PK |
| question, answer | TEXT |
| created_by | FK → USERS |

Vai trò: **fallback trước RAG** — LangGraph kiểm tra FAQ (match đơn giản) trước, không khớp mới gọi node RAG.

### DOCUMENTS
| Field | Type | Ghi chú |
|---|---|---|
| document_id | INT, PK | |
| title, file_path | VARCHAR | |
| uploaded_by, uploaded_at | FK / DATETIME | |

Nội dung PDF xử lý thành embeddings lưu Chroma riêng; bảng này chỉ quản lý metadata.

### APPLICATIONS (Phase 2 — giữ nguyên thiết kế gốc, chưa migrate ở GATE 2)
| Field | Type |
|---|---|
| application_id | INT, PK |
| user_id | FK → USERS |
| id_card_file, contract_file, payment_file | VARCHAR |
| status | ENUM(Pending, Approved, Need More Info, Rejected) |
| note, submitted_at, reviewed_at, reviewed_by | TEXT / DATETIME / FK |

## 7. Decisions & Assumptions Register

| Quyết định | Trạng thái | Nguồn | Cần ai chốt | Hạn |
|---|---|---|---|---|
| Checklist phải cá nhân hóa theo tình huống từng hộ | **Đã xác nhận — yêu cầu đề bài chính thức (Cơ bản)** (06/08) | Nguyên văn đề bài BTC, không phải giả định team | — | Đã chốt, không thương lượng |
| Trích nguồn tài liệu khi hướng dẫn thủ tục | **Đã xác nhận — yêu cầu đề bài chính thức (Cơ bản)** (06/08) | Nguyên văn đề bài BTC ("hướng dẫn từng bước có trích tài liệu") | — | Đã chốt |
| **Persona: chủ căn hộ là chính, có nhánh cho người thuê** | **Đã xác nhận — họp team 06/08** | Buyer = BQL nên ưu tiên đối tượng BQL quản lý trực tiếp (chủ hộ); người thuê vẫn phục vụ qua nhánh riêng. Bộ thuộc tính cá nhân hóa: `ownership_type` + loại căn/có xe/gói tiện ích (PRD) | — | Đã chốt — **backend được phép triển khai US-02/rule engine** |
| **Phạm vi quy trình: chỉ quy trình thuộc BQL; bên thứ ba (tạm trú/công an) chỉ hướng dẫn theo quy định công khai** | **Đã xác nhận — họp team 06/08** | Giải quyết vấn đề RAG không có tài liệu nội bộ BQL cho quy trình ngoài hệ thống. Cơ chế: `item_type` trên CHECKLIST_ITEMS | — | Đã chốt |
| **Chia role: AI / FE / BE; dữ liệu là việc chung cả team** | **Đã xác nhận — quyết định nhóm trưởng 06/08** | 2 rủi ro cần bù có chủ đích: dữ liệu "việc chung" cần phân task cụ thể theo tuần; ranh giới BE/AI giao nhau cần contract trước khi code (mục 3, mục 12) | — | Đã chốt |
| Auth dùng Supabase Auth thuần, bỏ password tự quản | **Đã xác nhận** (06/08) | Quyết định team trong buổi này | — | Đã chốt |
| FAQ là fallback trước RAG | **Đã xác nhận** (06/08) | Quyết định team trong buổi này | — | Đã chốt |
| APPLICATIONS (duyệt hồ sơ) giữ Phase 2 | **Đã xác nhận** (06/08) | Quyết định team trong buổi này — khớp với "HITL BQL duyệt hồ sơ" nằm trong mục Nâng cao của đề bài | — | Đã chốt |
| Scope địa lý: **Vinhomes Smart City**, 1 khu duy nhất, không multi-khu | **Đã xác nhận — họp team 06/08** (cụ thể hóa từ quyết định "1 khu" trước đó) | Quyết định team | — | Đã chốt |
| Giá trị cụ thể của `apartment_type` (những loại căn nào ở Smart City) | Còn mở | Cần dữ liệu thật khu Smart City | Cả team (data là việc chung) | 13/08 |
| Nội dung checklist thật (thẻ cư dân, thẻ xe, tiện ích...) | Còn mở | Chờ team thu thập (việc chung) | Cả team / mentor | **13/08 (cổng quyết định)** |
| Dashboard BQL nâng cao (biểu đồ/bộ lọc) — mức độ phức tạp | Còn mở | Ước lượng effort giả định | Mentor | Trước W5 |
| "Nộp hồ sơ online" — must-have hay Phase 2? | **Đã xác nhận** (06/08) — Phase 2 (W4-W5), Brief "must-have" là ghi chú cũ, không còn hiệu lực | Team: W2-W3 (hiện tại) chỉ tập trung 2 tính năng cốt lõi bắt buộc — tạo checklist + AI hỏi đáp thủ tục | — | Đã chốt |
| "Lấy form biểu mẫu" (tải template) | **Đã xác nhận** (06/08) — gộp cùng nhóm Phase 2 với "nộp hồ sơ online", không làm ở MVP W2-W3 | Team | — | Đã chốt |
| Buyer thật là ai | **Đã xác nhận** (06/08) — Buyer = **BQL**. Cư dân là end-user, được BQL phân bổ/cấp quyền truy cập app, không phải người trả tiền | Team | — | Đã chốt |
| Cư dân tự đăng ký hay được BQL cấp tài khoản? | **Đã xác nhận — họp team 06/08: BQL cấp/tạo tài khoản, cư dân KHÔNG tự tạo được** | Quyết định team — đảo ngược so với hướng nghiêng "tự đăng ký" trước đó | — | Đã chốt |
| **Checklist: lọc trực tiếp thay vì chốt cứng lúc onboarding** | **Đã xác nhận** (06/08, phiên thiết kế kiến trúc) | Bảng `CHECKLIST_COMPLETIONS` chỉ lưu mục đã xong. BQL cập nhật thủ tục → cư dân cũ thấy ngay; bỏ được logic đồng bộ/gộp | — | Đã chốt |
| **Cư dân sửa được hồ sơ sau onboarding** | **Đã xác nhận** (06/08) | Mua xe/đăng ký thêm tiện ích sau khi dọn vào là tình huống thực tế; với lọc trực tiếp thì không tốn thêm công | — | Đã chốt |
| **Checklist KHÔNG đi qua LangGraph** | **Đã xác nhận** (06/08) — đảo ngược quyết định "bọc thành node" trước đó trong cùng phiên | Graph 1 node bọc hàm thuần là thừa, dễ bị đánh giá là chưa hiểu LangGraph. Lập luận mạnh hơn: rule-based là lựa chọn có chủ đích, LangGraph dành cho chỗ cần quyết định thật | — | Đã chốt |
| **Hội thoại single-turn ở Phase 1** | **Đã xác nhận** (06/08) — giới hạn có ý thức, không phải sót | Multi-turn cần bước viết lại câu hỏi theo ngữ cảnh (~6-8h). Nên hỏi mentor chữ "memory" trong đề bài có hàm ý bộ nhớ hội thoại không | Mentor (làm rõ) | Cân nhắc Phase 2 |
| **Nhánh FAQ hoãn code sang W4** | **Đã xác nhận** (06/08) | Chi phí thật nằm ở hiệu chỉnh ngưỡng (cần dữ liệu thật), không phải ở code. RAG đơn thuần đã thoả mãn yêu cầu "hỏi đáp có trích tài liệu" của đề bài | — | Đã chốt |
| **KB cho GATE 2 dùng Thông tư 02/2016/TT-BXD** | Đề xuất từ phiên kiến trúc 06/08, **cần team xác nhận** | Cổng dữ liệu 13/08 nằm **sau** GATE 2 (12/08) → ngày demo vẫn có thể chưa có tài liệu BQL. Thông tư này công khai, tải được ngay, gắn `source_type: public_regulation` | Cả team | **Trong tuần này, không đợi 13/08** |
| Eval offline có được chấp nhận không | Còn mở — **tạm chưa cần bàn** (xác nhận 06/08) | Team quyết định hoãn, không phải việc gấp | Mentor | Trước W5, không gấp |
| Success metrics sản phẩm thật chưa có con số target | Còn mở — **tạm chưa cần bàn** (xác nhận 06/08) | Team quyết định hoãn, không phải việc gấp | Team/mentor | Trước US-15, không gấp |

## 8. Ràng buộc kỹ thuật

- **Stack bắt buộc, không đổi:** GPT-4o-mini · LangGraph · FastAPI · Next.js · Chroma · Supabase · PostgreSQL · Railway (backend) · Vercel (frontend)
- Rule engine phân loại cư dân: **rule-based, không LLM** — exact-match AND đơn giản trên `conditions` JSONB, không hỗ trợ OR/range (xem mục 7 để biết giới hạn đã chấp nhận)
- Code style: type hints bắt buộc, function ≤30 dòng, ≤3 params, không bare `except`, ruff pass trong CI
- AI usage logging: hoàn toàn tự động qua pre-push hook, không tự gọi log script thủ công

## 9. Chiến lược dữ liệu & cổng quyết định 13/08

5 nguồn song song: (1) Mentor làm kênh trung gian, (2) trang thông tin bên thứ ba (đối chiếu trước khi đưa vào KB), (3) kênh chính thức Vinhomes, (4) proxy qua cư dân thật, (5) khảo sát thực địa.

**Cổng 13/08:** ≥3 bộ tài liệu thật → dùng nguồn thật. 1-2 bộ → dùng làm khung, mở rộng bằng Thông tư 02/2016/TT-BXD. Không có bộ nào → chuyển hẳn phương án dự phòng, không kéo dài thêm.

## 10. Timeline & Mốc

Cố định theo chương trình: GATE 1 (05/08, đã qua) → báo cáo lần 2 (08/08) → GATE 2 demo MVP (12/08) → cổng dữ liệu (13/08) → embed KB (17/08, không được trễ) → Phase 1 hoàn thiện (19/08) → Phase 2 (20-26/08) → Demo Day (01/09).

## 11. Rủi ro & Giảm thiểu

| Rủi ro | Trạng thái |
|---|---|
| KB không có nội dung thật kịp deadline | Đang xử lý, cổng 13/08 |
| Chọn sai persona chính | Ảnh hưởng thấp — rule engine hỗ trợ cả hai loại |
| Dashboard BQL bị đánh giá thấp effort | Chưa xác nhận với mentor |
| **Tài liệu thiết kế (user story/schema/UI) trôi lệch nhau giữa 3 người** | **Rủi ro mới phát hiện 06/08** — xem mục 12 (Governance) |
| UI (`web/`) hiện toàn bộ mock, chưa có trang form onboarding | Đã xác nhận (đọc trực tiếp code nhánh `MinhThu`), cần FE bổ sung trang `/onboarding` |
| Dữ liệu KB là "việc chung cả team" — nguy cơ không ai làm | Rủi ro của mô hình role AI/FE/BE — giảm thiểu: phân task data cụ thể theo tuần trong WORKLOG.md |
| Nếu `login/page.tsx` hiện tại là form tự đăng ký (self-signup) | **Cần FE kiểm tra lại (06/08)** — quyết định "BQL cấp tài khoản, không tự đăng ký" nghĩa là không cần trang đăng ký công khai; thay vào đó BE/FE cần thêm màn hình BQL "tạo tài khoản cư dân" (US-00) |
| **Khối lượng Phase 1 (~120h) vượt sức 3 người trong 6 ngày tới GATE 2** | **Đã xử lý 06/08** — chia lát cắt `[GATE 2]` / `[W4]`, xem mục 4 |
| **Chưa có tài liệu KB nào để demo RAG ở GATE 2** — cổng dữ liệu 13/08 nằm SAU ngày demo 12/08 | Giảm thiểu: nạp Thông tư 02/2016/TT-BXD (công khai, tải ngay được) trong tuần này, không đợi cổng 13/08 |
| Chất lượng chunking kém → retrieval trả về đoạn sai, nhìn như "AI kém" dù code đúng | Hỏng thầm lặng, khó phát hiện. Bắt buộc kiểm tra thủ công 10 câu hỏi trước khi tin pipeline (xem ARCHITECTURE.md mục 11) |
| Cấu hình xác thực JWT Supabase sai → chặn toàn bộ API | Giới hạn 2h thử; chưa xong thì tạm dùng `supabase-py` gọi `auth.get_user(jwt)`, tối ưu sau |

## 12. Governance — quy trình đồng bộ liên vai trò

Lý do thêm mục này: buổi làm việc 06/08 phát hiện bộ user story/schema mới do nhóm soạn **mâu thuẫn trực tiếp** với quyết định cá nhân hóa checklist đã chốt trước đó, và UI hiện có (`web/`) chưa có trang form onboarding — không ai đối chiếu 2 tài liệu với nhau trước khi đưa cho backend triển khai.

**Quy tắc áp dụng từ nay:**
1. Mọi contract giữa các role phải viết ra thành tài liệu **trước khi** code, không dựng ngầm định: API contract giữa BE và FE (endpoint, request/response shape), và interface giữa BE và AI (schema state LangGraph, cấu trúc dữ liệu rule engine/checklist mà node agent đọc).
2. Thay đổi field/scope ảnh hưởng ≥2 người phải cập nhật vào mục 7 (Decisions Register) của file này — không sửa rải rác ở file cá nhân.
3. Trước khi bắt đầu 1 hạng mục kỹ thuật mới, kiểm tra nhanh mục 7 xem có quyết định nào đang "Còn mở" ảnh hưởng tới hạng mục đó không.
