> ⚠️ **File này đã là tài liệu lịch sử/tham khảo quá trình ra quyết định.** Nguồn sự thật hiện hành là [`PROJECT_CHARTER.md`](./PROJECT_CHARTER.md) (cập nhật 06/08/2026) — có scope, schema, user story đã sửa để khớp các quyết định mới nhất (checklist cá nhân hóa, Supabase Auth thuần, FAQ fallback...).

# MoveInMate — Tóm tắt bối cảnh dự án
**Mục đích file này:** cung cấp đầy đủ ngữ cảnh cho một agent/phiên làm việc khác tiếp tục hỗ trợ dự án mà không cần đọc lại toàn bộ lịch sử chat.

**Cập nhật lần cuối:** 05/08/2026

---

## 1. TỔNG QUAN DỰ ÁN

**Tên:** MoveInMate — AI Agent hỗ trợ onboarding cư dân chung cư

**Bối cảnh:** Đồ án nhóm 3 người, trong khuôn khổ một chương trình đào tạo/thực tập AI (cohort có tên "AI20K", nhắc tới trong slide "Master Timeline"). Đây là **chương trình do Vingroup tổ chức**, nên đề tài bắt buộc lấy bối cảnh chung cư Vinhomes.

**Vấn đề cần giải quyết:** Cư dân mới (chủ yếu là **người thuê**) tại các khu chung cư Vinhomes phải tự xoay xở với các thủ tục onboarding (làm thẻ cư dân, đăng ký tạm trú, thẻ xe...) mà không có ai hướng dẫn hệ thống. Theo mentor xác nhận, các thủ tục này hiện **vẫn do các phòng ban xử lý thủ công**, chưa có giải pháp phần mềm/agent nào.

**Định vị so với sản phẩm đã có:** Vinhomes đã có app "Vinhomes Resident" nhưng chỉ xử lý đặt tiện ích, thanh toán phí, gửi phản ánh — phục vụ cư dân *đã ổn định*. Hồ sơ giấy tờ và thẻ ra/vào vẫn phải làm việc trực tiếp qua BQL. MoveInMate lấp khoảng trống này — phục vụ **4-6 tuần đầu tiên** khi cư dân chưa biết mình cần làm gì.

---

## 2. NGƯỜI DÙNG & PERSONA

**Đối tượng chính: Người thuê** (không phải chủ sở hữu nhận bàn giao). Lý do:
- Xoay vòng liên tục (6-12 tháng/lượt) → khối lượng câu hỏi lặp lại cao hơn nhiều
- Chủ hộ nhận bàn giao có nhân viên dẫn qua từng bước; người thuê chỉ nhận chìa khóa từ chủ nhà rồi tự xoay
- Cần **nhiều giấy tờ hơn** chủ hộ, không phải ít hơn: CCCD + hợp đồng thuê + (có thể) ủy quyền + tạm trú/KT3, so với chủ hộ chỉ cần CCCD + giấy tờ căn hộ

**Đối tượng phụ: Chủ hộ** — vẫn hỗ trợ đầy đủ, không phải trọng tâm demo.

⚠️ Việc chọn người thuê làm persona chính là **suy luận của nhóm**, chưa được mentor xác nhận bằng dữ liệu thực nghiệm (phòng ban nào quá tải nhất). Cần hỏi lại mentor.

**Rẽ nhánh quan trọng nhất trong rule engine:** `ownership_type` (chủ hộ / người thuê) — làm thay đổi *nội dung* giấy tờ cần nộp, không chỉ có/không có bước. Đây là bằng chứng mạnh nhất để bảo vệ quyết định dùng rule-based.

---

## 3. SCOPE — ĐÃ QUA NHIỀU LẦN ĐIỀU CHỈNH

### Lịch sử scope (từ rộng → hẹp → phân pha)
1. Ban đầu (bản đặc tả đầu tiên): 4 user story ngang hàng — Persona Detection (LLM), Checklist Generation, RAG Knowledge Base, Request Creation & Routing
2. Nhóm tự đề xuất rút gọn còn 2 use case (Checklist + Hỏi đáp AI), bỏ hẳn phần routing/HITL
3. **Quyết định cuối cùng (đang áp dụng): phân pha, không cắt bỏ.** Pha 1 = lõi cho MVP, Pha 2 = nâng cao, làm sau nhưng vẫn làm đủ.

### Scope hiện tại — 2 pha

**Pha 1 — Lõi (bắt buộc có ở MVP GATE 2, 12/08)**
| Mã | Tính năng | Effort ước tính |
|---|---|---|
| US-01 | Form onboarding + rule-based profiling (không dùng LLM) | 8h |
| US-02 | Sinh checklist cá nhân hóa (lọc theo `conditions`, gồm `ownership_type`) | 20h |
| US-03 | Theo dõi tiến độ (tick, %, lưu trạng thái, persistence) | 12h |
| US-04 | RAG hỏi đáp có trích nguồn | 40h — đầu tư lớn nhất, là tính năng AI duy nhất |
| US-05 | Auth Supabase (2 role: cư dân, BQL) | 12h |

**Pha 2 — Nâng cao (làm ở W4-W5, không bị cắt, chỉ hoãn)**
| # | Tính năng | Effort | Ghi chú |
|---|---|---|---|
| 1 | Agent tạo yêu cầu (US-06) | 14h | Chỗ duy nhất agent phải ra quyết định → lý do tồn tại của LangGraph |
| 2 | HITL: BQL duyệt (US-07) | 12h | Ràng buộc bắt buộc của đề bài |
| 3 | Dashboard BQL (US-08) | 18h | Ước lượng giả định đơn giản (danh sách + nút); có thể tăng gấp đôi nếu cần biểu đồ/bộ lọc — **chưa xác nhận với mentor** |
| 4 | Định tuyến đa phòng ban (US-09) | 10h | Nâng cấp #1 từ 1 phòng lên N phòng |
| 5 | Nhắc việc còn thiếu (US-10) | 8h | Trong app (banner/badge), không email/SMS |
| 6 | Eval tỉ lệ hoàn tất (US-11) | 6h | **Làm offline**, không xây thành tính năng trong app — chạy 30 hồ sơ giả lập, đưa số liệu vào slide |

**Đã cắt hoàn toàn, không làm:** đa ngôn ngữ, upload/xác thực giấy tờ (OCR), thông báo email/SMS/Zalo, analytics nâng cao.

**Tổng effort ước tính: ~335h** (backend/logic ~175h, frontend ~85h, nội dung+QA ~75h).

---

## 4. QUYẾT ĐỊNH KỸ THUẬT QUAN TRỌNG

### Phân loại cư dân: Rule-based, KHÔNG dùng LLM
- Lý do: persona là tập hữu hạn thuộc tính nhị phân (chủ hộ/người thuê, có xe, có thú cưng, quốc tịch...), thu thập qua **form có cấu trúc** (6 câu chọn), không phải từ câu chat tự do
- Rule engine ~50 dòng code, lọc theo AND đơn giản trên trường `conditions` (JSONB)
- Tiết kiệm effort đáng kể: 8h thay vì 36h nếu dùng LLM
- Ngân sách LLM dồn hết cho US-04 (RAG) — nơi thực sự cần suy luận ngôn ngữ tự nhiên

### Vì sao vẫn giữ LangGraph dù persona không cần LLM
- Nếu chỉ có UC1 (checklist) + UC2 (RAG) thì luồng chỉ là form → query → trả lời, LangGraph không có việc gì để làm
- Giữ US-06 (agent tạo yêu cầu) làm chỗ agent phải **quyết định**: trả lời được (RAG đủ tự tin) hay phải tạo ticket cho BQL — đây là lý do LangGraph tồn tại trong kiến trúc

### Stack bắt buộc (từ đề bài, không đổi)
GPT-4o mini · LangGraph · FastAPI · Next.js · Chroma · Supabase · PostgreSQL · Railway (backend) · Vercel (frontend)

### Schema DB — nên dựng đủ ngay từ W3
Kể cả các bảng của Pha 2 (`tickets`, `departments`, `ticket_messages`) để tránh phải migrate giữa chừng ở W4. Chi phí ~2h ở W3, tiết kiệm ~10h sau này.

---

## 5. TÌNH HÌNH DỮ LIỆU (vấn đề đang xử lý, CHƯA GIẢI QUYẾT XONG)

### Đã xảy ra
- Mentor đề xuất khảo sát BQL Vinhomes tại buổi họp mentor lần 2 (01/08)
- Nhóm liên hệ BQL đầu tháng 8 (03-04/08) → **bị từ chối**, lý do BQL đưa ra: thủ tục đã công khai
- Tự tìm hiểu: tài liệu chỉ công khai **cho cư dân**, không công khai ra ngoài
- Hỏi bạn bè ở Vinhomes 1,2,3: nói thủ tục đơn giản, "chỉ 1 hợp đồng" — nhưng sau xác minh, mẫu này **không hợp lệ** vì họ thuê theo căn lẻ, không phải cư dân chung cư cao tầng Vinhomes thật

### Đã thử và không hiệu quả — KHÔNG lặp lại
- ❌ Liên hệ BQL trực tiếp (email/gọi lạnh)
- ❌ Group Facebook cư dân — chủ yếu để mua bán, hoặc là group private không truy cập được

### Chiến lược nguồn dữ liệu hiện tại (5 nguồn song song)
1. **Mentor làm kênh trung gian** (ưu tiên cao nhất) — xin file Sổ tay cư dân, giới thiệu đầu mối BQL, sơ đồ phòng ban
2. **Trang thông tin theo dự án** (bên thứ ba, kiểu vinhomessmartcitytaymo.com) — có thông tin khá chi tiết về hồ sơ/phí/thời gian, nhưng **phải đối chiếu với nguồn chính thức trước khi đưa vào KB**
3. **Kênh chính thức**: vinhomes.vn, app Vinhomes Resident, hotline CSKH 1900 23 23 89
4. **Proxy qua cư dân thật** — nhờ 1 người bạn là cư dân Vinhomes cao tầng thật vào group của họ tìm bằng chứng câu hỏi lặp (chụp màn hình), không cần tự vào group
5. **Khảo sát thực địa** — đến trực tiếp Smart City/Ocean Park, chụp bảng tin công khai ở sảnh, quan sát quầy BQL, trò chuyện với cư dân

### Nguồn dữ liệu đã tìm được qua web search (cần nhóm tự xác minh lại)
- Hồ sơ làm thẻ cư dân: **Chủ hộ** cần CCCD + giấy tờ căn hộ + ảnh 3×4; **Khách thuê** cần CCCD + hợp đồng thuê + (nếu cần) ủy quyền + ảnh 3×4 + tạm trú/KT3. Thời gian xử lý: trong ngày đến 24-72h, tùy tòa
- App Vinhomes Resident: đăng ký dịch vụ thẻ cư dân/ra vào/xe/thang máy, thanh toán phí, gửi yêu cầu hỗ trợ — nhưng hồ sơ cư dân và thẻ ra/vào **vẫn phải làm việc qua BQL của tòa**, không tự động qua app
- ⚠️ Nguồn trên lấy từ trang bên thứ ba, độ tin cậy trung bình, chưa được Vinhomes hoặc mentor xác nhận

### Hai loại "dữ liệu giả" — phân biệt rõ, không được nhầm lẫn
| Loại | Được phép? |
|---|---|
| Bịa **nội dung KB** (thủ tục, giấy tờ, phí, thời hạn) | **KHÔNG** — RAG sẽ trả lời sai sự thật |
| Sinh **hồ sơ cư dân giả** để test/eval | **CÓ** — chuẩn mực bình thường, chỉ cần ghi rõ phương pháp |

### Phương án dự phòng (nếu đến 13/08 vẫn không có tài liệu thật)
Xây KB từ Thông tư 02/2016/TT-BXD (Quy chế quản lý sử dụng nhà chung cư) + tài liệu công khai, **ghi rõ nguồn ở metadata mỗi tài liệu**, và khai báo thẳng trong báo cáo: "KB tổng hợp từ nguồn công khai, chưa được BQL xác nhận trực tiếp — giới hạn đã biết, đưa vào phần Hướng phát triển tiếp theo."

### Cổng quyết định: 13/08 (thứ 5, W3)
- Có ≥3 bộ tài liệu thật → tiếp tục dùng nguồn thật
- Có 1-2 bộ → dùng làm khung, mở rộng bằng Thông tư 02/2016
- Không có bộ nào → chuyển hẳn sang phương án dự phòng, không kéo dài thêm

---

## 6. TIMELINE CHƯƠNG TRÌNH (cố định, không đổi)

Từ slide "Master Timeline" của chương trình (cohort AI20K):

```
Tuần 1     Tuần 2 (GATE 1)   Tuần 3 (GATE 2)   Tuần 4        Tuần 5              Tuần 6
Kick-off   Chốt đề tài       Xây dựng MVP      Tối ưu,       Nộp hồ sơ,          Demo Day
& lập đội  Khảo sát,         đầu tiên          cải thiện     hoàn thiện sản      01/09/2026
           phân tích                           dựa trên      phẩm
                                                feedback
```

**Mốc thực tế đã xảy ra (khác với lịch chương trình một chút):**
- 26/07: chương trình chốt danh sách nhóm chính thức
- 29/07: họp mentor lần 1 — thảo luận, đề xuất đề tài MoveInMate
- 31/07: **hạn chót chốt đề tài** chính thức
- 01/08: họp mentor lần 2 — mentor đề xuất khảo sát BQL Vinhomes. **Nhóm chỉ bắt đầu làm việc nghiêm túc từ mốc này**, không phải từ 26/07
- 03-04/08: nhóm liên hệ BQL, bị từ chối
- 05/08 (hôm nay, thứ 4): báo cáo GATE 1

**Các mốc sắp tới, cố định:**
- 05/08 (Wed): GATE 1 — báo cáo roadmap, use case, user story, xin góp ý mentor
- 08/08 (Sat): báo cáo lần 2 sau khi chỉnh sửa theo góp ý
- 12/08 (Wed): GATE 2 — demo MVP (chỉ Pha 1: form → checklist cá nhân hóa → tiến độ → hỏi đáp RAG)
- 13/08 (Thu): cổng quyết định nguồn dữ liệu (mục 5)
- 17/08 (Mon, W4): bắt đầu embed toàn bộ 15 tài liệu KB — **mốc này không được trễ**
- 19/08 (W4 kết thúc): Pha 1 chạy thật hoàn toàn, không còn mock
- 20/08 (W5 bắt đầu): làm Pha 2 (nâng cao)
- 26/08 (W5 kết thúc): triển khai Railway + Vercel, nộp hồ sơ dự án
- 01/09 (Tue): DEMO DAY

---

## 7. PHÂN CÔNG NHÓM

| Người | Vai trò | Việc chính |
|---|---|---|
| **Person A** | Dữ liệu & QA | Viết nội dung KB (đường găng của UC2), thu thập dữ liệu thật, test RAG liên tục, chuẩn bị hồ sơ giả lập cho eval |
| **Person B** | Backend & Agent Logic | **Critical path.** Rule engine, schema DB, pipeline RAG, LangGraph, agent quyết định tạo ticket |
| **Person C** | Frontend | Form onboarding, trang checklist/chat, dashboard BQL, responsive design |

**Đường găng đã dịch chuyển theo thời gian:** ban đầu nghẽn ở code (Person B phải làm 4 tính năng), sau khi rút gọn persona sang rule-based thì nghẽn chuyển sang **nội dung KB** (Person A) — vì RAG có code hoàn chỉnh cũng vô dụng nếu không có tài liệu để truy xuất.

---

## 8. RỦI RO ĐANG THEO DÕI

| Rủi ro | Trạng thái |
|---|---|
| KB không có nội dung thật kịp deadline | **Đang xử lý tích cực**, cổng quyết định 13/08 |
| Hội đồng hỏi "đã có app Vinhomes Resident rồi, sao cần cái này?" | Đã chuẩn bị câu trả lời (mục 1 — định vị sản phẩm), cần đưa vào slide |
| Hội đồng hỏi "vấn đề có thật không?" | Cần ≥10 bằng chứng câu hỏi lặp từ cư dân thật (nguồn 4, mục 5) |
| Tài liệu từ trang bên thứ ba sai lệch | Chưa xác minh — cần đối chiếu trước khi đưa vào KB |
| Chọn sai persona chính (người thuê vs chủ hộ) | Ảnh hưởng thấp — rule engine hỗ trợ cả hai, chỉ ảnh hưởng trọng tâm demo |
| Dashboard BQL (US-08) bị đánh giá thấp effort | Ước lượng 18h giả định đơn giản, **chưa xác nhận với mentor** mức độ phức tạp kỳ vọng |
| Pha 2 dồn hết vào W5 | Đã có biện pháp: khởi động US-06 từ thứ 6 W4, không đợi W5 |
| Mốc 17/08 (embed KB) bị trễ | Cổng 13/08 tồn tại chính để chặn rủi ro này |

---

## 9. CÂU HỎI CÒN MỞ (cần mentor hoặc nhóm tự quyết)

1. Phòng ban nào ở Vinhomes đang quá tải nhất vì xử lý thủ công? → xác nhận persona chính (người thuê) bằng dữ liệu thực, không chỉ suy luận
2. Dashboard BQL kỳ vọng đơn giản (danh sách + nút duyệt) hay cần biểu đồ/bộ lọc/phân trang?
3. Eval tỉ lệ hoàn tất làm offline (đưa số liệu vào slide) có được chấp nhận khi bảo vệ, hay bắt buộc phải là tính năng trong app?
4. Nếu đến 13/08 không có tài liệu KB thật, phương án dự phòng (Thông tư 02/2016 + khai báo giới hạn) có chấp nhận được không?
5. Mentor có mối quan hệ nào với BQT hoặc đơn vị vận hành để giới thiệu nhóm tiếp cận không?

---

## 10. FILE THAM CHIẾU KHÁC ĐÃ TẠO TRONG DỰ ÁN

- `MoveInMate_User_Stories.md` / `.xlsx` — đặc tả chi tiết 4 user story theo template "Đặc tả tính năng" (US-01 đến US-04, phiên bản cũ trước khi rút gọn scope)
- `MoveInMate_Project_Management.xlsx` — file quản lý dự án chính thức của nhóm (theo template chương trình), sheet "Lộ trình" đã được cập nhật với các mốc M1-M8 khớp timeline thực tế
- Các bản roadmap v1-v6 (markdown) — lịch sử điều chỉnh scope, hiện **v6 hoặc bản mới nhất là bản có hiệu lực**, các bản cũ chỉ để tham khảo quá trình ra quyết định

**Lưu ý cho agent tiếp theo:** nếu người dùng nhắc đến "roadmap", nên hỏi rõ đang muốn xem/sửa file nào (markdown tổng quan hay file Excel "Lộ trình" chính thức), vì cả hai đang tồn tại song song và có thể lệch nhau nếu không đồng bộ cẩn thận.
