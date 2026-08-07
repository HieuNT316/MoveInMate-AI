# Weekly Journal — MoveInMate (Team P-225)

> Ghi lại mỗi tuần: học được gì, khó khăn gì, quyết định gì, kế hoạch tiếp.
> Nguồn sự thật về scope và quyết định: [`docs/PROJECT_CHARTER.md`](./docs/PROJECT_CHARTER.md)

---

## Week 1: 23/07 - 29/07 — Lập đội & tìm đề tài

### Mục tiêu tuần này
- [x] Hoàn tất lập đội, chốt danh sách thành viên
- [x] Tìm và đề xuất đề tài với mentor

### Đã hoàn thành
- 26/07 — chương trình chốt danh sách nhóm chính thức
- 29/07 — họp mentor lần 1, thảo luận và đề xuất đề tài MoveInMate (AI agent hỗ trợ onboarding cư dân chung cư)

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Chưa rõ đề tài nào vừa sức vừa có giá trị thực tế | Bám bối cảnh chương trình do Vingroup tổ chức, chọn bài toán onboarding cư dân Vinhomes | Mentor đồng ý hướng đi |

### Bài học
- Đề tài gắn với bối cảnh có thật của đơn vị tổ chức dễ bảo vệ hơn đề tài chung chung.

### Kế hoạch tuần sau
- [x] Chốt đề tài chính thức trước hạn 31/07
- [x] Bắt đầu tìm hiểu quy trình thật tại Vinhomes

---

## Week 2: 30/07 - 05/08 — Chốt đề tài & GATE 1

### Mục tiêu tuần này
- [x] Chốt đề tài chính thức (hạn 31/07)
- [x] Khảo sát quy trình onboarding thật tại Vinhomes
- [x] Báo cáo GATE 1 (05/08)

### Đã hoàn thành
- 31/07 — chốt đề tài MoveInMate đúng hạn
- 01/08 — họp mentor lần 2; mentor đề xuất khảo sát BQL Vinhomes. **Nhóm thực sự bắt đầu làm việc nghiêm túc từ mốc này**, không phải từ 26/07
- 02/08 — soạn PRD v0.1 (bối cảnh, khách hàng mục tiêu, scope P0/P1/P2, luồng người dùng, yêu cầu phi chức năng)
- 03-04/08 — liên hệ BQL Vinhomes xin tài liệu quy trình
- 05/08 — báo cáo GATE 1: roadmap, use case, user story

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| **BQL từ chối cung cấp tài liệu**, lý do "thủ tục đã công khai" | Chuyển sang chiến lược nhiều nguồn song song: mentor làm kênh trung gian, trang thông tin dự án, kênh chính thức Vinhomes, proxy qua cư dân thật, khảo sát thực địa | Chưa có tài liệu chính thức; đặt cổng quyết định 13/08 để không kéo dài vô hạn |
| Tài liệu công khai chỉ mở cho cư dân, không mở ra ngoài | Xác định phương án dự phòng: dựng KB từ Thông tư 02/2016/TT-BXD + nguồn công khai, ghi rõ nguồn ở metadata | Có đường lui, không bị chặn hoàn toàn |
| Hỏi bạn bè ở Vinhomes 1,2,3 thì được trả lời "thủ tục đơn giản, chỉ 1 hợp đồng" | Xác minh lại | Mẫu không hợp lệ — họ thuê căn lẻ, không phải cư dân chung cư cao tầng |

### Bài học
- **Không nên trông chờ vào một nguồn dữ liệu duy nhất.** Việc BQL từ chối là rủi ro có thể lường trước; đáng lẽ nên chuẩn bị phương án dự phòng ngay từ khi đề xuất khảo sát.
- Xác minh mẫu trước khi tin vào thông tin phỏng vấn — người trả lời có thể không thuộc nhóm đối tượng mình cần.
- Liên hệ lạnh tới doanh nghiệp gần như không có tác dụng; kênh qua người quen/mentor hiệu quả hơn nhiều.

### Kế hoạch tuần sau
- [x] Chuẩn hóa lại toàn bộ tài liệu dự án thành một nguồn sự thật duy nhất
- [x] Thiết kế kiến trúc hệ thống
- [ ] Dựng MVP cho GATE 2 (12/08)

---

## Week 3: 06/08 - 12/08 — Chuẩn hóa tài liệu, thiết kế kiến trúc & MVP

### Mục tiêu tuần này
- [x] Lập PROJECT_CHARTER làm nguồn sự thật duy nhất
- [x] Thiết kế kiến trúc hệ thống, viết ARCHITECTURE
- [x] Chuẩn bị môi trường và thư viện cho Phase 1
- [ ] Dựng MVP: đăng nhập → form onboarding → checklist cá nhân hóa → tiến độ → hỏi đáp RAG
- [ ] Nạp KB tạm cho demo GATE 2
- [ ] Demo GATE 2 (12/08)

### Đã hoàn thành
- 06/08 — lập `docs/PROJECT_CHARTER.md`, phát hiện và xử lý một loạt mâu thuẫn giữa các tài liệu nội bộ (xem phần Khó khăn)
- 06/08 — chốt persona: chủ căn hộ là chính, có nhánh cho người thuê; phạm vi chỉ Vinhomes Smart City
- 06/08 — chốt phạm vi quy trình: chỉ hỗ trợ đầy đủ thủ tục thuộc BQL; thủ tục bên thứ ba chỉ hướng dẫn theo quy định công khai
- 06/08 — thiết kế và viết `docs/architecture_diagram.md`
- 06/08 — ghim phiên bản thư viện, cài đủ dependency Phase 1 cho cả backend và frontend
- 06/08 — phân role chính thức: Hiếu (BE + Data), Hải (AI), Thu (FE)

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| **Các tài liệu của nhóm mâu thuẫn nhau** — bộ user story/schema mới bỏ hẳn tính cá nhân hóa, trong khi PRD và đề bài đều yêu cầu; PRD dùng bộ thuộc tính khác hẳn tài liệu tóm tắt bối cảnh | Đối chiếu tất cả tài liệu với **đề bài gốc**, lập PROJECT_CHARTER làm nguồn sự thật duy nhất, kèm sổ ghi quyết định phân biệt rõ "đã xác nhận" và "còn giả định" | Hết mâu thuẫn; mọi quyết định về sau đều ghi vào một chỗ |
| Nhầm lẫn về người dùng chính — tưởng là người thuê, thực tế người thuê không dùng được app Vinhomes Resident và phải làm tạm trú qua công an | Tách vấn đề theo **loại quy trình** thay vì theo loại người dùng: quy trình thuộc BQL hỗ trợ đầy đủ, quy trình bên thứ ba chỉ hướng dẫn tham khảo | Phục vụ được cả chủ hộ lẫn người thuê mà không vi phạm yêu cầu "trích nguồn, không bịa" |
| Khối lượng Phase 1 (~120h) vượt xa 6 ngày còn lại tới GATE 2 | Cắt Phase 1 thành hai lát: `[GATE 2]` bắt buộc và `[W4]` làm sau. Hoãn nhánh FAQ, giao diện upload, dashboard, PWA | Lát cắt GATE 2 vừa sức, vẫn đủ chứng minh giá trị sản phẩm |
| Cổng dữ liệu 13/08 nằm **sau** ngày demo 12/08 → có nguy cơ không có tài liệu nào để RAG truy xuất lúc demo | Dùng Thông tư 02/2016/TT-BXD (công khai, tải được ngay) làm KB cho GATE 2, gắn `source_type: public_regulation` | Không còn phụ thuộc việc BQL có hợp tác hay không |

### Bài học
- **Tài liệu do nhiều người soạn độc lập sẽ trôi lệch nhau nếu không có nguồn sự thật duy nhất.** Triệu chứng chỉ lộ ra khi ghép lại để code, lúc đó đã tốn công.
- **Đối chiếu ngược lên đề bài gốc trước khi tranh luận nội bộ.** Nhóm suýt bỏ tính cá nhân hóa — thứ mà đề bài ghi rõ trong yêu cầu Cơ bản, tức là bắt buộc chấm điểm.
- Phân biệt "đã xác nhận" và "đang giả định" trong tài liệu quan trọng không kém việc ghi lại quyết định. Một giả định cá nhân bị tưởng là quyết định của cả nhóm đã dẫn tới thiết kế sai hướng.
- Ước lượng effort phải đặt cạnh deadline mới có ý nghĩa. Kiến trúc đúng cho Phase 1 chưa chắc là thứ làm kịp trong 6 ngày.

### Kế hoạch tuần sau
- [ ] Hoàn thiện phần còn lại của Phase 1 (nhánh FAQ, upload tài liệu, dashboard BQL, PWA)
- [ ] Nạp toàn bộ KB thật — mốc 17/08 không được trễ
- [ ] Hiệu chỉnh ngưỡng FAQ bằng câu hỏi thật

---

## Week 4: 13/08 - 19/08

### Mục tiêu tuần này
- [ ] Cổng quyết định nguồn dữ liệu (13/08)
- [ ] Nạp toàn bộ KB (17/08 — không được trễ)
- [ ] Phase 1 chạy với dữ liệu thật, không còn mock (19/08)

### Đã hoàn thành
-

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| | | |

### Bài học
-

### Kế hoạch tuần sau
-

---

## Week 5: 20/08 - 26/08

### Mục tiêu tuần này
- [ ] Phase 2: agent tạo ticket, HITL BQL duyệt hồ sơ, định tuyến phòng ban, nhắc việc
- [ ] Triển khai Railway + Vercel
- [ ] Nộp hồ sơ dự án (26/08)

### Đã hoàn thành
-

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| | | |

### Bài học
-

### Kế hoạch tuần sau
-

---

## Week 6: 27/08 - 01/09 — Demo Day

### Mục tiêu tuần này
- [ ] Hoàn thiện pitch deck và video demo
- [ ] Chạy eval, đưa số liệu vào slide
- [ ] Demo Day (01/09)

### Đã hoàn thành
-

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| | | |

### Bài học
-
