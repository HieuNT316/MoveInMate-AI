# Báo cáo mentor — MoveInMate | 08/08/2026

**Kỳ báo cáo:** 05/08 (GATE 1) → 08/08 · **Nhóm P-225** · Trình bày ~5 phút + demo ~5 phút

---

## 1. Một câu tóm tắt

Ba ngày qua nhóm chuyển từ *ý tưởng rời rạc* sang **hệ thống chạy được end-to-end**: đã có kiến trúc chốt, DB thật, dữ liệu thật, và luồng cá nhân hóa checklist demo được. Phần AI (RAG) và xác thực Supabase là hai mảng **chưa bắt đầu**, đúng là rủi ro lớn nhất cho GATE 2 ngày 12/08.

---

## 2. Đối chiếu roadmap

| Mốc | Hạn | Trạng thái |
|---|---|---|
| GATE 1 | 05/08 | ✅ Đã qua |
| **Báo cáo lần 2** | **08/08** | 🔵 Hôm nay |
| GATE 2 — demo MVP | 12/08 | ⏳ Còn 4 ngày |
| Cổng dữ liệu | 13/08 | ⚠️ Đã xử lý sớm (xem mục 4) |
| Embed KB | 17/08 | ⏳ |
| Phase 1 hoàn thiện | 19/08 | ⏳ |

### Lát cắt `[GATE 2]` — bắt buộc xong 12/08

| ID | Tính năng | Trạng thái |
|---|---|---|
| US-00 | BQL cấp tài khoản cư dân | ✅ API xong |
| US-01 | Auth qua Supabase | ❌ **Chưa bắt đầu** — đang dùng đăng nhập tạm không mật khẩu |
| US-02 | Form onboarding + rule-based profiling | ✅ Xong cả BE và FE |
| US-03/04 | Checklist cá nhân hóa + tiến độ | ✅ Xong, có test |
| US-05 | RAG hỏi đáp có trích nguồn | ❌ **Chưa bắt đầu** — chat đang trả lời bằng dữ liệu giả |
| US-06/07 | Xem/sửa hồ sơ, lịch sử chat | ✅ Xong |
| — | Nạp KB bằng script CLI | 🟡 Đã có dữ liệu, chưa có pipeline embed |

**5/7 hạng mục xong. Hai hạng mục còn lại là hai hạng mục nặng nhất.**

---

## 3. Đã làm được

### 3.1 Định hướng — gỡ được rủi ro lớn nhất

Phát hiện 07/08: tài liệu thiết kế của ba người **trôi lệch nhau** (user story, schema, luồng UI mô tả ba sản phẩm hơi khác nhau). Xử lý:

- Lập `docs/PROJECT_CHARTER.md` làm **nguồn sự thật duy nhất**, có *Decisions & Assumptions Register* tách bạch "đã chốt" và "còn giả định"
- Lập `docs/architecture_diagram.md` — 11 mục, 5 sơ đồ Mermaid, bảng ADR
- Quy tắc governance: **chốt hợp đồng bằng văn bản trước khi code**

Chốt được 15+ quyết định từng mơ hồ, đáng kể nhất:

| Quyết định | Lý do |
|---|---|
| Buyer = **BQL**, cư dân là end-user được cấp tài khoản | Cư dân không tự đăng ký được |
| Phân loại checklist bằng **rule-based, không LLM** | Thủ tục hành chính cần đúng tuyệt đối, không cần suy luận |
| Checklist **lọc trực tiếp**, không chốt cứng lúc onboarding | BQL sửa thủ tục thì cư dân cũ thấy ngay |
| Tách `item_type`: BQL xử lý vs thủ tục bên thứ ba | Không tính tạm trú (công an) vào KPI của BQL |
| Cắt scope thành `[GATE 2]` / `[W4]` | Phase 1 ~120h, 3 người 5 ngày = 8h/người/ngày — không thực tế |

### 3.2 Dữ liệu — vượt tiến độ

Cổng dữ liệu là 13/08, **sau** ngày demo 12/08. Nhóm không đợi, đã thu thập xong hôm nay:

| Nguồn | Nội dung | Quy mô |
|---|---|---|
| `data/kb/web/` | 7 trang thủ tục Vinhomes Smart City (thẻ cư dân, tạm trú, phí gửi xe, phí dịch vụ, thanh toán, app, hotline) | 42.684 token |
| `data/kb/legal/` | Quy chế quản lý nhà chung cư — 5 chương, 50 điều | 63.965 token |
| **Tổng** | | **106.649 token ≈ 295 chunk** |

Hai script cào tự động, chạy lại được: `scripts/scrape_kb.py`, `scripts/fetch_legal_kb.py`.

**Một phát hiện đáng lưu ý:** kế hoạch ban đầu định dùng **Thông tư 02/2016/TT-BXD**. Kiểm tra lại thì văn bản này **đã hết hiệu lực từ 01/08/2024**, bị thay bởi Thông tư 05/2024/TT-BXD theo Luật Nhà ở 2023. Với sản phẩm lấy *trích nguồn* làm giá trị cốt lõi, nạp văn bản hết hiệu lực sẽ tạo ra câu trả lời sai kèm trích dẫn trông rất đáng tin. Đã đổi sang văn bản hiện hành.

### 3.3 Code — chạy được end-to-end

| Hạng mục | Chi tiết |
|---|---|
| Rule engine | `src/services/checklist.py` — hàm thuần, validate `conditions` khi seed để chặn lỗi gõ nhầm |
| Schema DB | 6 bảng + Alembic migration, test cả `upgrade` lẫn `downgrade` |
| Dữ liệu demo | 40 cư dân + 12 checklist item, **tất định** (seed cố định) nên ba máy ra cùng một bộ |
| API | 12 endpoint, chạy trên DB thật |
| Frontend | 9 route, đã nối API thật, có trang onboarding |
| Chất lượng | **52 test pass**, ruff sạch, CI xanh |

---

## 4. Demo — 5 phút

| # | Thao tác | Điểm cần thấy |
|---|---|---|
| 1 | Mở trang đăng nhập | Danh sách persona, **mỗi người hiện sẵn số mục checklist khác nhau** |
| 2 | Đăng nhập *chủ hộ, có ô tô, gói hồ bơi + gym* | Checklist **10 mục** |
| 3 | Đổi sang *người thuê, không xe* | Checklist **6 mục** |
| 4 | Đổi sang *chủ hộ, studio, không xe* | Cũng **6 mục** — nhưng **nội dung khác**: "thẻ cư dân (chủ hộ)" + "cập nhật cư trú" thay vì "thẻ cư dân (người thuê)" + "đăng ký tạm trú" |
| 5 | Vào Hồ sơ → bấm "Đổi" ở mục Có xe | Checklist **tự lên 8 mục**, tiến độ tụt 50% → 37% vì mẫu số tăng — minh hoạ lọc trực tiếp |
| 6 | Chat: *"làm thẻ xe cần giấy tờ gì"* | Trả lời **kèm trích nguồn** |
| 7 | Chat: *"thời tiết Hà Nội hôm nay"* | **Từ chối trả lời** thay vì bịa |
| 8 | Đăng nhập BQL | Dashboard 40 cư dân, tiến độ chỉ tính thủ tục thuộc BQL |

**Bước 4 là điểm quan trọng nhất.** Nhìn con số thì tưởng giống nhau, mở ra mới thấy rule engine phân nhánh — đây là thứ chứng minh sản phẩm không phải một checklist tĩnh.

> ⚠️ Cần nói rõ với mentor: **bước 6-7 hiện chạy trên dữ liệu giả**, chưa phải RAG thật.

---

## 5. Đang vướng

| Vấn đề | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| **Chưa tạo Supabase project** | Chặn US-01 (auth thật) và chặn FE. Đây là việc của tôi, đã trễ 1 ngày | Làm ngay tối nay |
| **RAG chưa bắt đầu** | Hạng mục nặng nhất (~30h), là phần "AI" mà đề bài chấm | Dữ liệu đã sẵn sàng, AI bắt đầu ngay 09/08 |
| Đăng nhập tạm **không kiểm mật khẩu** | Không được lên production | Xoá khi có Supabase Auth |
| 3 checklist item chưa có tài liệu nguồn | Ký nội quy, chỗ đỗ xe cố định, đăng ký chuyển đồ | Cần xin BQL, hoặc bỏ khỏi checklist |
| Chưa có deploy, eval, video, pitch deck | Deliverable bắt buộc | Sau GATE 2 |

**Nhìn thẳng:** trong 3 ngày qua khối lượng commit tập trung gần hết ở vai BE+Data. Hai vai còn lại bắt đầu từ 09/08 theo kế hoạch, nhưng phần FE bị chặn một phần do tôi chưa tạo Supabase project đúng hạn.

---

## 6. Câu hỏi cho mentor

### Về yêu cầu đề bài

1. **Chữ "memory" trong đề bài** có hàm ý bộ nhớ hội thoại multi-turn không? Nhóm đang làm **single-turn** (mỗi câu hỏi độc lập) vì multi-turn cần thêm bước viết lại câu hỏi theo ngữ cảnh (~6-8h). Nếu bắt buộc thì phải cắt việc khác.

2. **Rule-based có bị coi là "chưa đủ AI" không?** Nhóm cố ý **không dùng LLM** cho phân loại checklist — thủ tục hành chính cần đúng tuyệt đối và giải thích được, LLM chỉ thêm rủi ro. LangGraph chỉ dùng cho nhánh hỏi đáp. Cách chia này có được chấp nhận khi chấm không?

3. **Dashboard BQL** cần đến mức nào? Hiện chỉ định làm danh sách + % tiến độ (~5h). Có cần biểu đồ, bộ lọc không?

### Về dữ liệu

4. **Nguồn không chính thức có được dùng không?** 40% KB đến từ một trang cộng đồng (`vinhomessmartcitytaymo.com`), không phải trang chính thức của BQL. Nhóm đã gắn nhãn `unofficial_web` và `is_official: false`. Nếu đến 13/08 BQL không cung cấp tài liệu thì demo bằng nguồn này có bị trừ điểm không, và nên hiển thị cảnh báo thế nào cho đúng?

5. **Corpus đang lệch 60% văn bản pháp quy / 40% nội dung Vinhomes.** Câu hỏi "phí gửi xe bao nhiêu" không nên bị kéo về điều luật. Nên xử lý bằng metadata filter hay nên cân lại tỷ lệ?

### Về đánh giá

6. **Eval offline có được chấp nhận không**, hay bắt buộc phải có người dùng thật? Nhóm dự định tự soạn ~25-30 câu hỏi và chấm retrieval accuracy thủ công.

7. **Ngưỡng nào là "đạt"** cho retrieval accuracy? Nhóm đang tự đặt mục tiêu ≥7/10.

### Về quản trị

8. **Còn 4 ngày tới GATE 2 mà hai hạng mục nặng nhất chưa bắt đầu.** Nếu buộc phải hy sinh một thứ, mentor khuyên hy sinh cái nào: **auth thật** (giữ đăng nhập tạm) hay **RAG thật** (giữ câu trả lời mẫu)? Nhóm nghiêng về giữ RAG và hy sinh auth, vì RAG là phần được chấm.

---

## 7. Kế hoạch 4 ngày tới

| Ngày | Hiếu (BE+Data) | Hải (AI) | Thu (FE) |
|---|---|---|---|
| 09/08 | Supabase + auth thật | Chunk + embed, đo retrieval ≥7/10 | Form onboarding |
| 10/08 | API cư dân hoàn thiện | Dựng LangGraph | Checklist thật |
| 11/08 | Tích hợp + deploy Railway | Test + LangSmith | Chat + deploy Vercel |
| 12/08 | Dự phòng + tổng duyệt demo | Chuẩn bị câu hỏi demo | Responsive |

**Chốt chặn:** Hải phải đạt ≥7/10 retrieval accuracy **trước khi** viết node LangGraph. Không đạt thì sửa chunking, không đi tiếp.
