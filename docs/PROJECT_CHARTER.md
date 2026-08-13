# PROJECT CHARTER — MoveInMate

> Tài liệu chính thức, là nguồn sự thật (single source of truth) cho scope, kiến trúc và quyết định của dự án.
> Kiến trúc kỹ thuật chi tiết: [`architecture_diagram.md`](./architecture_diagram.md).
>
> *(Bản tóm tắt bối cảnh cũ `MoveInMate_Context_Summary.md` đã được gỡ bỏ ngày 07/08 — nội dung của nó đã được chuẩn hoá và thay thế hoàn toàn bởi tài liệu này. Cần tra lịch sử thì xem git.)*

**Cập nhật lần cuối:** 07/08/2026
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

**⚠️ Quan trọng:** "Cá nhân hóa" và "theo tình huống từng hộ" xuất hiện ở cả phần Vấn đề lẫn Yêu cầu Cơ bản — đây là **yêu cầu chấm điểm bắt buộc của đề bài**, không phải lựa chọn kiến trúc của nhóm. Bỏ cá nhân hóa = không đáp ứng đúng đề tài, không phải vấn đề chất lượng thực thi. (Xác nhận 07/08, xem mục 7.)

**Vấn đề (diễn giải theo bối cảnh Vinhomes):** Cư dân mới tại chung cư Vinhomes phải tự xoay xở với thủ tục onboarding (thẻ cư dân, thẻ xe, tiện ích...) mà không có hướng dẫn hệ thống hóa. Các thủ tục này hiện do phòng ban xử lý thủ công, chưa có giải pháp phần mềm/agent nào.

**Định vị so với Vinhomes Resident app:** App hiện có chỉ xử lý đặt tiện ích, thanh toán phí, gửi phản ánh — phục vụ cư dân *đã ổn định*. Hồ sơ giấy tờ và thẻ ra/vào vẫn phải làm việc trực tiếp qua BQL. MoveInMate lấp khoảng trống này — phục vụ **4-6 tuần đầu tiên** khi cư dân chưa biết mình cần làm gì, với điểm khác biệt cốt lõi là **checklist cá nhân hóa theo hồ sơ cư dân** (không phải danh sách chung chung).

**Persona (xác nhận 07/08, chốt sau họp team):** **Chủ căn hộ là persona chính**, có thêm **nhánh cho người thuê**. Buyer thật là **BQL** (mục 3), nên ưu tiên đúng đối tượng BQL quản lý trực tiếp là chủ hộ; người thuê vẫn được phục vụ nhưng qua nhánh riêng. Cơ sở cá nhân hóa: `ownership_type` (owner/renter) xác định nhánh + giấy tờ khác nhau cho các thủ tục **thuộc phạm vi BQL**; loại căn hộ/có xe/gói tiện ích (theo PRD) xác định các bước tiện ích cụ thể. Chi tiết cơ chế: xem mục 6 và mục 7.

**Phạm vi quy trình (xác nhận 07/08):** App chỉ xử lý đầy đủ (tracking, HITL, trích nguồn từ tài liệu nội bộ) các thủ tục **thuộc phạm vi BQL** (thẻ cư dân, thẻ xe, tiện ích...). Các thủ tục thuộc bên thứ ba (vd. tạm trú/lưu trú qua công an) **chỉ đưa hướng dẫn tham khảo theo quy định chung công khai hiện hành**, không tracking/HITL, nguồn trích dẫn ghi rõ là quy định pháp luật công khai (không phải tài liệu nội bộ BQL) để tránh vi phạm NFR "tránh bịa thông tin". Cơ chế: field `item_type` trên `CHECKLIST_ITEMS` (mục 6).

**Scope địa lý (xác nhận 07/08):** **Vinhomes Smart City** — 1 khu cụ thể, không multi-khu. Câu "chính xác theo từng khu" trong đề bài hiểu là đảm bảo thông tin đúng với khu được chọn.

## 2. Mục tiêu & Success Criteria

| Mốc | Tiêu chí "xong" |
|---|---|
| GATE 2 (12/08) | Form onboarding (chủ hộ + nhánh người thuê) → checklist cá nhân hóa theo `ownership_type`/loại căn/xe/tiện ích → tiến độ → hỏi đáp AI → Dashboard BQL tối giản, chạy end-to-end, dù KB có thể còn placeholder |
| W4 kết thúc (19/08) | Toàn bộ Phase 1 chạy với dữ liệu thật, không còn mock |
| Demo Day (01/09) | ≥35/50 điểm theo tiêu chí BTC (Product ≥8, System ≥7, UI/UX ≥7, DevOps ≥6, Code ≥7) |

## 3. Stakeholders & Roles

**Phân role (chốt 07/08):** chia theo **AI / FE / BE**, dữ liệu thuộc về BE.

| Thành viên | Role | Việc chính |
|---|---|---|
| Nguyễn Trung Hiếu | **BE + Data** | FastAPI, schema DB, rule engine checklist, Supabase Auth, deploy Railway, **thu thập và chuẩn bị tài liệu KB** |
| Nguyễn Việt Hải | **AI** | Pipeline RAG, LangGraph, prompt, chunking, FAQ fallback, eval chất lượng trả lời |
| Nguyễn Minh Thu | **FE** | UI Next.js (`web/`) — hiện dashboard/login/profile/checklist/chat đều là mock; cần thêm form onboarding |
| Mentor (Đặng Hải Lộc) | — | Tư vấn, đầu mối giới thiệu BQL (nếu có) |
| BTC (AI20K Cohort 3) | — | Chấm điểm, cung cấp `AI_LOG_API_KEY`, hạ tầng logging |

Kế hoạch chi tiết theo ngày cho từng người: [`ROLES_AND_PLAN.md`](./ROLES_AND_PLAN.md).

> ✅ **Rủi ro "dữ liệu là việc chung, dễ không ai làm" đã được xử lý** — khi phân tích mô hình AI/FE/BE (07/08) tôi nêu hai điểm cần bù; điểm thứ nhất nay đã giải quyết vì Hiếu nhận luôn phần dữ liệu, có người chịu trách nhiệm rõ ràng.
>
> ⚠️ **Điểm thứ hai vẫn còn:** ranh giới BE (schema, rule engine) và AI (LangGraph state) giao nhau — hai người phải thống nhất contract trước khi code, xem mục 12.

**Khách hàng sản phẩm (business, xác nhận 07/08):** Buyer = **BQL** (đơn vị trả tiền/triển khai). Cư dân là end-user, được BQL phân bổ/cấp quyền truy cập app — không phải người ra quyết định mua hay trả phí. Mọi ưu tiên tính năng nên phục vụ đúng nhu cầu BQL (giảm tải trả lời lặp lại, theo dõi tiến độ cư dân) trước, cư dân là người thụ hưởng gián tiếp.

## 4. Scope

### Phase 1 — Lõi

**Chia hai lát cắt (quyết định 07/08):** tổng effort Phase 1 ~120h, chia 3 người trong 5 ngày còn lại tới GATE 2 là ~8h/người/ngày không nghỉ — không thực tế. Nên phần bắt buộc cho 12/08 được cắt gọn lại, phần còn lại vẫn thuộc Phase 1 nhưng làm ở W4 (hạn 19/08).

**Lát cắt `[GATE 2]` — bắt buộc xong 12/08:**

| ID | Tính năng | Effort |
|---|---|---|
| US-00 (mới, 07/08) | BQL tạo/cấp tài khoản cư dân (không tự đăng ký) | ~4h |
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
| US-10 | Duyệt hồ sơ/giấy tờ (APPLICATIONS: CCCD, hợp đồng, thanh toán) | 12h | **Cập nhật 11/08:** phần *nộp* (form online + `POST /applications` tối giản, mã theo dõi + trạng thái) kéo lên sớm phục vụ agent điều hướng — xem register. Phần *duyệt* (Approved/Rejected/HITL) vẫn Phase 2 |
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
| US-00 | BQL | Tạo/cấp tài khoản cho cư dân | Cư dân có thể đăng nhập — *mới, hệ quả của quyết định "không tự đăng ký" (07/08)* |
| US-01 | Cư dân | Đăng nhập bằng tài khoản do BQL cấp (Supabase Auth) | Dùng hệ thống |
| US-02 | Cư dân | **Điền form onboarding** (ownership_type, loại căn hộ, có xe, gói tiện ích) | Hệ thống tạo checklist cá nhân hóa — *là mắt xích bắt buộc để US-04 hoạt động* |
| US-03 | Cư dân | Xem Dashboard | Tổng quan chức năng + trạng thái hồ sơ |
| US-04 | Cư dân | Xem Checklist cá nhân hóa & tick hoàn thành | Theo dõi tiến độ nhận nhà |
| US-05 | Cư dân | Hỏi AI (FAQ fallback → RAG có trích nguồn) | Giải đáp thủ tục nhận nhà |
| US-06 | Cư dân | Xem **và sửa** hồ sơ | Kiểm tra/cập nhật thông tin cá nhân, căn hộ, persona — sửa xong checklist tự cập nhật (xác nhận 07/08) |
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

*Đã bỏ so với bản trước (07/08): `has_pet`, `nationality`, `has_power_of_attorney`, `household_size` — không nằm trong bộ thuộc tính đã chốt (ownership_type + loại căn/xe/gói tiện ích theo PRD). Thêm lại khi có bằng chứng thủ tục thật cần tới.*

### CHECKLIST_ITEMS (bảng template — team seed nội dung chung)
| Field | Type | Ghi chú |
|---|---|---|
| checklist_item_id | INT, PK | |
| task_name | VARCHAR | |
| description | TEXT, nullable | |
| category | VARCHAR, nullable | |
| item_type | ENUM(bql_actionable, third_party_info) | **Mới (07/08):** `bql_actionable` = thủ tục BQL xử lý, có tracking/HITL/trích nguồn nội bộ; `third_party_info` = quy trình bên thứ ba (tạm trú/công an...), chỉ hướng dẫn tham khảo theo quy định công khai, cư dân tự tick, không HITL |
| conditions | JSONB | `{}` = áp dụng mọi người; vd `{"ownership_type":"renter"}`. Với `amenity_packages` (multi-select): value đơn được hiểu là "nằm trong danh sách", vd `{"amenity_packages":"pool"}` khớp user có pool trong gói. **Validate key phải khớp field hợp lệ của USERS khi seed** (chặn lỗi gõ nhầm) |
| order_index | INT | |

### CHECKLIST_COMPLETIONS (đổi tên + đổi thiết kế 07/08 — chỉ lưu mục ĐÃ hoàn thành)
| Field | Type | Ghi chú |
|---|---|---|
| completion_id | INT, PK | |
| user_id | FK → USERS | |
| checklist_item_id | FK → CHECKLIST_ITEMS | |
| completed_at | DATETIME | Có dòng = đã xong; không có dòng = chưa xong |
| | UNIQUE(user_id, checklist_item_id) | |

**Lọc trực tiếp, không chốt cứng checklist lúc onboarding.** Danh sách hiển thị được tính lại mỗi lần `GET /checklist`: lọc `CHECKLIST_ITEMS` theo profile hiện tại → left join bảng này. Lý do đổi (07/08): (a) BQL cập nhật thủ tục thì cư dân cũ thấy ngay, không cần logic đồng bộ; (b) cư dân sửa hồ sơ thì checklist tự cập nhật, không cần logic gộp dễ mất dữ liệu; (c) không phát sinh câu hỏi khó "mục đã tick nhưng không còn khớp điều kiện thì xử lý sao".

Tiến độ tính tại query time, không cần bảng PROGRESS riêng. **Trả về hai con số cho hai đối tượng** (chốt 08/08 khi rà soát API):

- `overall` — mọi mục khớp `conditions`, dành cho cư dân xem
- `bql_scope` — chỉ mục `item_type = bql_actionable`, dành cho dashboard BQL và cho eval US-15

Lý do tách: gộp chung sẽ khiến BQL thấy cư dân "chậm" vì một thủ tục mà chính BQL không xử lý được, không xác nhận được và không giúp gì được (vd. tạm trú ở công an). Buyer là BQL nên tín hiệu vận hành của họ phải sạch.

`onboarding_completed_at` **chỉ ghi ở lần hoàn thành đầu tiên**, submit lại không ghi đè — metric "% cư dân hoàn thành onboarding trong X ngày đầu" (PRD) cần mốc đầu tiên chứ không phải lần gần nhất.

### CHAT_HISTORY (bổ sung field trích nguồn — yêu cầu cốt lõi của US-05)
| Field | Type | Ghi chú |
|---|---|---|
| chat_id | INT, PK | |
| user_id | FK → USERS | |
| question, answer | TEXT | |
| answer_source | ENUM(faq, rag, no_context) | Câu trả lời đến từ FAQ, RAG, hay không tìm được tài liệu. Đổi tên khỏi `source_type` để không trùng nghĩa với `source_type` của từng nguồn tài liệu (bql_internal / public_regulation) |
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
| Checklist phải cá nhân hóa theo tình huống từng hộ | **Đã xác nhận — yêu cầu đề bài chính thức (Cơ bản)** (07/08) | Nguyên văn đề bài BTC, không phải giả định team | — | Đã chốt, không thương lượng |
| Trích nguồn tài liệu khi hướng dẫn thủ tục | **Đã xác nhận — yêu cầu đề bài chính thức (Cơ bản)** (07/08) | Nguyên văn đề bài BTC ("hướng dẫn từng bước có trích tài liệu") | — | Đã chốt |
| **Persona: chủ căn hộ là chính, có nhánh cho người thuê** | **Đã xác nhận — họp team 06/08** | Buyer = BQL nên ưu tiên đối tượng BQL quản lý trực tiếp (chủ hộ); người thuê vẫn phục vụ qua nhánh riêng. Bộ thuộc tính cá nhân hóa: `ownership_type` + loại căn/có xe/gói tiện ích (PRD) | — | Đã chốt — **backend được phép triển khai US-02/rule engine** |
| **Phạm vi quy trình: chỉ quy trình thuộc BQL; bên thứ ba (tạm trú/công an) chỉ hướng dẫn theo quy định công khai** | **Đã xác nhận — họp team 06/08** | Giải quyết vấn đề RAG không có tài liệu nội bộ BQL cho quy trình ngoài hệ thống. Cơ chế: `item_type` trên CHECKLIST_ITEMS | — | Đã chốt |
| **Chia role: AI / FE / BE; dữ liệu là việc chung cả team** | **Đã xác nhận — quyết định nhóm trưởng 07/08** | 2 rủi ro cần bù có chủ đích: dữ liệu "việc chung" cần phân task cụ thể theo tuần; ranh giới BE/AI giao nhau cần contract trước khi code (mục 3, mục 12) | — | Đã chốt |
| Auth dùng Supabase Auth thuần, bỏ password tự quản | **Đã xác nhận** (07/08) | Quyết định team trong buổi này | — | Đã chốt |
| **US-01 đã triển khai xong 11/08** — đăng nhập bằng mật khẩu qua Supabase, BE verify JWT | **Đã thực hiện** | Project ký token **ES256 + JWKS**, KHÔNG phải HS256 — `SUPABASE_JWT_SECRET` vô dụng ở đây. 41 tài khoản đã cấp qua `scripts/provision_auth.py` | — | Đã chốt |
| **`X-User-Id` giữ làm lối dev, chặn cứng khi `APP_ENV=production`** | **Đã chốt 11/08** | Không chặn thì ai cũng đặt `X-User-Id` của BQL để thành BQL. Giữ lại để bộ đổi persona demo còn chạy và FE chuyển dần không đứt | — | Gỡ hẳn khi bỏ `/auth/demo-accounts` |
| **US-00 tạo tài khoản trả về mật khẩu tạm thay vì gửi email mời** | **Đã chốt 11/08** | `invite_user_by_email` cần SMTP và email có thật; dữ liệu demo dùng tên miền không tồn tại nên thư không bao giờ tới. Mật khẩu chỉ hiện đúng một lần, hệ thống không lưu | — | Xem lại khi có cư dân thật |
| FAQ là fallback trước RAG | **Đã xác nhận** (07/08) | Quyết định team trong buổi này | — | Đã chốt |
| APPLICATIONS (duyệt hồ sơ) giữ Phase 2 | **Đã xác nhận** (07/08) | Quyết định team trong buổi này — khớp với "HITL BQL duyệt hồ sơ" nằm trong mục Nâng cao của đề bài | — | Đã chốt |
| Scope địa lý: **Vinhomes Smart City**, 1 khu duy nhất, không multi-khu | **Đã xác nhận — họp team 06/08** (cụ thể hóa từ quyết định "1 khu" trước đó) | Quyết định team | — | Đã chốt |
| Giá trị cụ thể của `apartment_type` (những loại căn nào ở Smart City) | Còn mở | Cần dữ liệu thật khu Smart City | Cả team (data là việc chung) | 13/08 |
| Nội dung checklist thật (thẻ cư dân, thẻ xe, tiện ích...) | Còn mở | Chờ team thu thập (việc chung) | Cả team / mentor | **13/08 (cổng quyết định)** |
| Dashboard BQL nâng cao (biểu đồ/bộ lọc) — mức độ phức tạp | Còn mở | Ước lượng effort giả định | Mentor | Trước W5 |
| "Nộp hồ sơ online" — must-have hay Phase 2? | **Đã xác nhận** (07/08) — Phase 2 (W4-W5), Brief "must-have" là ghi chú cũ, không còn hiệu lực | Team: W2-W3 (hiện tại) chỉ tập trung 2 tính năng cốt lõi bắt buộc — tạo checklist + AI hỏi đáp thủ tục | — | Đã chốt |
| "Lấy form biểu mẫu" (tải template) | **Đã xác nhận** (07/08) — gộp cùng nhóm Phase 2 với "nộp hồ sơ online", không làm ở MVP W2-W3 | Team | — | Đã chốt |
| Buyer thật là ai | **Đã xác nhận** (07/08) — Buyer = **BQL**. Cư dân là end-user, được BQL phân bổ/cấp quyền truy cập app, không phải người trả tiền | Team | — | Đã chốt |
| Cư dân tự đăng ký hay được BQL cấp tài khoản? | **Đã xác nhận — họp team 06/08: BQL cấp/tạo tài khoản, cư dân KHÔNG tự tạo được** | Quyết định team — đảo ngược so với hướng nghiêng "tự đăng ký" trước đó | — | Đã chốt |
| **Checklist: lọc trực tiếp thay vì chốt cứng lúc onboarding** | **Đã xác nhận** (07/08, phiên thiết kế kiến trúc) | Bảng `CHECKLIST_COMPLETIONS` chỉ lưu mục đã xong. BQL cập nhật thủ tục → cư dân cũ thấy ngay; bỏ được logic đồng bộ/gộp | — | Đã chốt |
| **Cư dân sửa được hồ sơ sau onboarding** | **Đã xác nhận** (07/08) | Mua xe/đăng ký thêm tiện ích sau khi dọn vào là tình huống thực tế; với lọc trực tiếp thì không tốn thêm công | — | Đã chốt |
| **Checklist KHÔNG đi qua LangGraph** | **Đã xác nhận** (07/08) — đảo ngược quyết định "bọc thành node" trước đó trong cùng phiên | Graph 1 node bọc hàm thuần là thừa, dễ bị đánh giá là chưa hiểu LangGraph. Lập luận mạnh hơn: rule-based là lựa chọn có chủ đích, LangGraph dành cho chỗ cần quyết định thật | — | Đã chốt |
| ~~Hội thoại single-turn ở Phase 1~~ **→ Đảo ngược: multi-turn đã làm (13/08)** | **Đã xác nhận** (07/08), **đảo ngược 13/08** theo yêu cầu team, **chưa hỏi mentor** như dự định ban đầu | Thêm node `rewrite_query` viết lại câu hỏi mơ hồ ("còn phí thì sao?") thành độc lập ngữ cảnh trước khi truy xuất, dùng N lượt gần nhất của ĐÚNG hội thoại đang mở (`conversation_id` mới, migration `ddfa7af31680`). Lịch sử chỉ vào bước viết lại câu hỏi, KHÔNG vào thẳng `generate` — giữ nguyên bảo đảm chống bịa. Câu hỏi "memory" trong đề bài vẫn CHƯA được mentor xác nhận — rủi ro: có thể đã làm việc ngoài đúng ý BTC | — (đã làm, không còn cần mentor để bắt đầu, nhưng NÊN hỏi để biết có đúng hướng BTC chấm hay không) | Xong ở Phase 1 |
| **Nhánh FAQ hoãn code sang W4** | **Đã xác nhận** (07/08) | Chi phí thật nằm ở hiệu chỉnh ngưỡng (cần dữ liệu thật), không phải ở code. RAG đơn thuần đã thoả mãn yêu cầu "hỏi đáp có trích tài liệu" của đề bài | — | Đã chốt |
| **KB cho GATE 2 dùng Thông tư 05/2024/TT-BXD** | **Đã thực hiện 08/08** — đảo ngược đề xuất 02/2016/TT-BXD của phiên kiến trúc 07/08 | 02/2016 **hết hiệu lực 01/08/2024**, bị thay bởi 05/2024/TT-BXD theo Luật Nhà ở 2023. Nạp văn bản hết hiệu lực vào hệ thống có trích nguồn = trả lời sai kèm trích dẫn đáng tin. Đã tải phần Quy chế (Điều 1-50) vào `data/kb/legal/`, gắn `source_type: public_regulation` | — | Đã chốt |
| Eval offline có được chấp nhận không | Còn mở — **tạm chưa cần bàn** (xác nhận 07/08) | Team quyết định hoãn, không phải việc gấp | Mentor | Trước W5, không gấp |
| Success metrics sản phẩm thật chưa có con số target | Còn mở — **tạm chưa cần bàn** (xác nhận 07/08) | Team quyết định hoãn, không phải việc gấp | Team/mentor | Trước US-15, không gấp |
| **Mục tiêu demo (mentor, họp 08/08): chứng minh ý tưởng + tính khả thi + khả năng "thực chiến" — KHÔNG yêu cầu dữ liệu chính xác với thực tế; được sinh dữ liệu hoặc dùng nguồn ngoài (Kaggle...) khi khó thu thập** | **Đã chốt — mentor xác nhận 08/08** | Gỡ ràng buộc lớn nhất của cổng dữ liệu 13/08 (mục 9 đã cập nhật theo) | — | Đã chốt |
| **`source_type` thứ tư: `synthetic_demo`** — quy trình do nhóm dựng, neo theo quy định thật (Điều 6/7/13 Quy chế) và hotline/bảng phí công khai; **số liệu phí KHÔNG được tự đặt**, phải trích nguồn công khai hoặc ghi rõ "đơn vị vận hành quy định" | **Đã thực hiện 11/08** | UI gắn nhãn "Quy trình mô phỏng (dữ liệu demo)" — minh bạch trước khi bị hỏi | — | Đã chốt |
| **Chat LLM: mặc định gọi thẳng OpenAI (đúng stack BTC), OpenRouter là lựa chọn qua `CHAT_PROVIDER`** — cùng model gpt-4o-mini, chỉ khác đường gọi | **Đã thực hiện 11/08** — thay cấu hình chỉ-OpenRouter ngày 10/08 của AI | Key OpenAI (trả phí) đã có; kiểm chứng bằng gọi thật cả 2 đường | — | Đã chốt |
| **Embeddings dùng Google `gemini-embedding-001` (3072 chiều)** — không phải OpenAI | Còn mở — **lệch stack BTC, cần mentor xác nhận** | OpenRouter không có endpoint embeddings (bối cảnh quyết định gốc của AI). CẢNH BÁO: `text-embedding-3-large` của OpenAI cũng 3072 chiều — đổi nguồn embed mà không re-ingest sẽ hỏng im lặng, Chroma không báo lỗi | Mentor | Trước 17/08 (mốc embed KB) |
| **APPLICATIONS-mini kéo lên trước hạn: form nộp hồ sơ online (FE) + `POST /applications` tối giản (mã theo dõi, trạng thái)** — đảo một phần quyết định "giữ Phase 2" ngày 07/08 | **Quyết định nhóm trưởng 10-11/08** (chỉ đạo FE làm form; mentor muốn demo một phần agent điều hướng) | Điều kiện: chốt contract schema/API bằng văn bản TRƯỚC khi FE và BE code song song (mục 12). Phần duyệt hồ sơ đầy đủ (Pending/Approved/...) vẫn ở Phase 2 | — | Đã chốt |
| **"Agent điều hướng" có BA nghĩa, phải gọi tách bạch:** (a) điều hướng trong app tới form/màn hình — tool `request_submission_navigation` (10/08); (b) **cho biết** đúng bộ phận, bước kế, thời hạn — chat trả lời được nhờ `data/kb/bql/` (11/08); (c) **nhận đơn online rồi chuyển tới đúng bộ phận BQL xử lý** — chính là **US-13 + US-10**, nguyên văn đề bài mục Nâng cao (mục 2), **Phase 2, chưa làm gì** | **Sửa 12/08** — bản ghi 11/08 chỉ nêu (a) và (b), bỏ sót (c) | Sai sót phân tích: định nghĩa thuật ngữ bằng code đang có thay vì tra ngược yêu cầu, dù US-13 nằm cùng file. (a) và (b) là *chỉ đường*; (c) là *thay mặt cư dân nộp* — khác nhau về bản chất. Việc gán đơn cho bộ phận **không cần LLM** (tra bảng, như rule engine checklist); chỗ cần agent là trả lời "hồ sơ tôi tới đâu rồi" | Nhóm trưởng | Quyết định có kéo US-13/US-10 lên Phase 1 hay không |
| **`data/chroma/` commit vào git** (index đã embed, ~7.3MB nhị phân) | **Quyết định AI 10/08** — đã ghi đánh đổi trong `.gitignore` | Quy ước bắt buộc: CHỈ MỘT người chạy `ingest_kb` rồi commit; người khác chỉ pull. Bằng chứng rủi ro: 11/08 chính BE đã lỡ `git checkout -- data/chroma/` sau khi ingest → mất kết quả, phải chạy lại | — | Đã chốt, xem lại khi lên Railway Volume |
| Góp ý UX của mentor (08/08): gamification khi hoàn thành thủ tục (huy hiệu/trang trí hồ sơ — KHÔNG hứa ưu đãi tiền thay BQL), câu trả lời chat có cấu trúc + hình minh hoạ | Ghi nhận — xếp W4, không bắt buộc GATE 2 | Ảnh trang nguồn là placeholder lazy-load không cào được; hướng đi: ảnh theo `category`, card có cấu trúc | Team | W4 |
| **LangSmith đang được KHAI mà chưa làm** — README, `requirements.txt` và sơ đồ kiến trúc đều ghi, `src/` không có dòng nào | **Phát hiện 11/08 — phải xử lý** | Đây là deliverable #4 của BTC. Bật bằng biến môi trường, không phải sửa code (~30 phút) | Hải | Trước GATE 2 nếu kịp, chậm nhất W4 |
| **Không có giới hạn tần suất trên URL công khai** | **Phát hiện 11/08 — rủi ro tiền thật** | Mỗi lượt `/chat` tốn 1 embedding + 1 LLM call trên key trả phí. Đề xuất `slowapi`, 20 lượt/phút/người | Hiếu | Trước khi công bố URL rộng rãi |
| **`/health` không kiểm thành phần phụ thuộc** | **Phát hiện 11/08** | Trả `ok` kể cả khi DB/Chroma chết → Railway giữ instance hỏng trong vòng phục vụ. Tiền lệ: index Chroma hỏng 11/08 mà mọi chỉ báo vẫn xanh | Hiếu | W4 |
| **Chưa có: log có cấu trúc, theo dõi chi phí, vòng phản hồi người dùng, che PII trong `chat_history`** | Ghi nhận 11/08 — xếp W4 | Chi tiết và mức ưu tiên: [`OPERATIONS.md`](./OPERATIONS.md) | Cả nhóm | W4-W5 |

## 8. Ràng buộc kỹ thuật

- **Stack bắt buộc, không đổi:** GPT-4o-mini · LangGraph · FastAPI · Next.js · Chroma · Supabase · PostgreSQL · Railway (backend) · Vercel (frontend)
- Rule engine phân loại cư dân: **rule-based, không LLM** — exact-match AND đơn giản trên `conditions` JSONB, không hỗ trợ OR/range (xem mục 7 để biết giới hạn đã chấp nhận)
- Code style: type hints bắt buộc, function ≤30 dòng, ≤3 params, không bare `except`, ruff pass trong CI
- AI usage logging: hoàn toàn tự động qua pre-push hook, không tự gọi log script thủ công

## 9. Chiến lược dữ liệu (cập nhật 11/08 theo quyết định mentor 08/08)

**Mentor đã gỡ ràng buộc "dữ liệu phải thật":** mục tiêu demo là chứng minh ý tưởng + khả thi, nên được sinh dữ liệu hoặc dùng nguồn ngoài khi khó thu thập. Cổng 13/08 vì thế đổi ý nghĩa — không còn là "có/không có tài liệu BQL" mà là **rà soát chất lượng và nhãn nguồn** của KB hiện có.

**Trạng thái KB (11/08, 386 chunk trong Chroma):**

| Thư mục | Nguồn | `source_type` | Ghi chú |
|---|---|---|---|
| `data/kb/web/` (7 file) | Trang cộng đồng VSC, cào bằng `scripts/scrape_kb.py` | `unofficial_web` | Phí, thẻ cư dân, tạm trú, app, hotline |
| `data/kb/legal/` (1 file) | Quy chế kèm TT 05/2024/TT-BXD, `scripts/fetch_legal_kb.py` | `public_regulation` | 02/2016 đã hết hiệu lực — không dùng |
| `data/kb/bql/` (3 file) | **Nhóm tự sinh 11/08** — cơ cấu bộ phận, bảng định tuyến thủ tục, luồng xử lý 5 bước, thủ tục còn trống | `synthetic_demo` | Neo Điều 6/7/13 Quy chế + hotline/bảng phí công khai; UI gắn nhãn mô phỏng |

**Kỷ luật sinh dữ liệu (bắt buộc):** chỉ sinh *quy trình/thủ tục*; **số liệu phí phải trích từ nguồn công khai** — không có số thì ghi "theo bảng giá đơn vị vận hành", không tự đặt. Mọi file sinh phải có frontmatter `source_type: synthetic_demo` + `is_official: false` + `grounded_on:` chỉ rõ neo. Vi phạm nhãn = coi như bug chặn merge.

**Việc còn lại của cổng 13/08:** nếu xin được tài liệu BQL thật thì thay dần file `synthetic_demo` tương ứng (giữ nguyên tên thủ tục để khỏi vỡ eval); không xin được cũng **không chặn** tiến độ nữa.

## 10. Timeline & Mốc

Cố định theo chương trình: GATE 1 (05/08, đã qua) → báo cáo lần 2 (08/08) → GATE 2 demo MVP (12/08) → cổng dữ liệu (13/08) → embed KB (17/08, không được trễ) → Phase 1 hoàn thiện (19/08) → Phase 2 (20-26/08) → Demo Day (01/09).

## 11. Rủi ro & Giảm thiểu

| Rủi ro | Trạng thái |
|---|---|
| KB không có nội dung thật kịp deadline | Đang xử lý, cổng 13/08 |
| Chọn sai persona chính | Ảnh hưởng thấp — rule engine hỗ trợ cả hai loại |
| Dashboard BQL bị đánh giá thấp effort | Chưa xác nhận với mentor |
| **Tài liệu thiết kế (user story/schema/UI) trôi lệch nhau giữa 3 người** | **Rủi ro mới phát hiện 07/08** — xem mục 12 (Governance) |
| UI (`web/`) hiện toàn bộ mock, chưa có trang form onboarding | Đã xác nhận (đọc trực tiếp code nhánh `MinhThu`), cần FE bổ sung trang `/onboarding` |
| Dữ liệu KB là "việc chung cả team" — nguy cơ không ai làm | Rủi ro của mô hình role AI/FE/BE — giảm thiểu: phân task data cụ thể theo tuần trong WORKLOG.md |
| Nếu `login/page.tsx` hiện tại là form tự đăng ký (self-signup) | **Cần FE kiểm tra lại (07/08)** — quyết định "BQL cấp tài khoản, không tự đăng ký" nghĩa là không cần trang đăng ký công khai; thay vào đó BE/FE cần thêm màn hình BQL "tạo tài khoản cư dân" (US-00) |
| **Khối lượng Phase 1 (~120h) vượt sức 3 người trong 6 ngày tới GATE 2** | **Đã xử lý 07/08** — chia lát cắt `[GATE 2]` / `[W4]`, xem mục 4 |
| **Chưa có tài liệu KB nào để demo RAG ở GATE 2** — cổng dữ liệu 13/08 nằm SAU ngày demo 12/08 | **Đã xử lý 08/08:** `data/kb/legal/` (Quy chế kèm TT 05/2024) + `data/kb/web/` (7 trang thủ tục Vinhomes Smart City) — tổng ~107k token, 295 chunk |
| Chất lượng chunking kém → retrieval trả về đoạn sai, nhìn như "AI kém" dù code đúng | Hỏng thầm lặng, khó phát hiện. Bắt buộc kiểm tra thủ công 10 câu hỏi trước khi tin pipeline (xem `docs/architecture_diagram.md` mục 11) |
| Cấu hình xác thực JWT Supabase sai → chặn toàn bộ API | Giới hạn 2h thử; chưa xong thì tạm dùng `supabase-py` gọi `auth.get_user(jwt)`, tối ưu sau |
| **Dữ liệu mô phỏng bị trình bày như dữ liệu thật trước doanh nghiệp** — mất uy tín ngay khi trong phòng có người biết số thật | Nhãn `synthetic_demo` xuyên suốt (frontmatter → Chroma metadata → badge UI "Quy trình mô phỏng") + một câu minh bạch trong lời dẫn demo |
| **Tool điều hướng của LLM bắn không ổn định** (đo 11/08: 2/4 cách hỏi; thêm data càng ít bắn vì LLM tự trả lời được bằng chữ) | Lớp đối chiếu tất định ở BE (`_match_checklist_item` chạy luôn, tool LLM hạ thành gợi ý); demo dùng câu đã kiểm chứng |
| **Ngưỡng `rag_max_distance=0.35` mong manh** — cụm "có đáp án" (~0.27-0.33) và "ngoài phạm vi" (~0.37-0.38) chỉ cách ~0.04, hiệu chỉnh mới trên 4 câu | Không vặn ngưỡng trước GATE 2; sau GATE 2 đo lại trên bộ ≥10 câu; đã giảm thin-coverage bằng data 11/08 |
| **Guard chống bịa hỏng ở vùng biên** — đo 11/08: chặn 4/4 câu ngoài lĩnh vực nhưng **0/3** câu "đúng lĩnh vực, KB không có dữ liệu"; câu trả lời nói "không tìm thấy" mà vẫn gắn `answer_source: rag` kèm trích dẫn | Cao — người dùng không có cách nào biết hệ thống đang không biết | Sửa hiển thị trước (phát hiện câu từ chối → đổi `no_context`, bỏ nguồn), hiệu chỉnh ngưỡng sau khi có đủ dữ liệu. Xem `eval/results/report.md` mục 2.2 |

## 12. Governance — quy trình đồng bộ liên vai trò

Lý do thêm mục này: buổi làm việc 07/08 phát hiện bộ user story/schema mới do nhóm soạn **mâu thuẫn trực tiếp** với quyết định cá nhân hóa checklist đã chốt trước đó, và UI hiện có (`web/`) chưa có trang form onboarding — không ai đối chiếu 2 tài liệu với nhau trước khi đưa cho backend triển khai.

**Quy tắc áp dụng từ nay:**
1. Mọi contract giữa các role phải viết ra thành tài liệu **trước khi** code, không dựng ngầm định: API contract giữa BE và FE (endpoint, request/response shape), và interface giữa BE và AI (schema state LangGraph, cấu trúc dữ liệu rule engine/checklist mà node agent đọc).
2. Thay đổi field/scope ảnh hưởng ≥2 người phải cập nhật vào mục 7 (Decisions Register) của file này — không sửa rải rác ở file cá nhân.
3. Trước khi bắt đầu 1 hạng mục kỹ thuật mới, kiểm tra nhanh mục 7 xem có quyết định nào đang "Còn mở" ảnh hưởng tới hạng mục đó không.
