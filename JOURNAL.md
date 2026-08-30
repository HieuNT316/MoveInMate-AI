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

## Week 3: 07/08 - 12/08 — Chuẩn hóa tài liệu, thiết kế kiến trúc & MVP

### Mục tiêu tuần này
- [x] Lập PROJECT_CHARTER làm nguồn sự thật duy nhất
- [x] Thiết kế kiến trúc hệ thống, viết ARCHITECTURE
- [x] Chuẩn bị môi trường và thư viện cho Phase 1
- [ ] Dựng MVP: đăng nhập → form onboarding → checklist cá nhân hóa → tiến độ → hỏi đáp RAG
- [ ] Nạp KB tạm cho demo GATE 2
- [ ] Demo GATE 2 (12/08)

### Đã hoàn thành
- 07/08 — lập `docs/PROJECT_CHARTER.md`, phát hiện và xử lý một loạt mâu thuẫn giữa các tài liệu nội bộ (xem phần Khó khăn)
- 07/08 — chốt persona: chủ căn hộ là chính, có nhánh cho người thuê; phạm vi chỉ Vinhomes Smart City
- 07/08 — chốt phạm vi quy trình: chỉ hỗ trợ đầy đủ thủ tục thuộc BQL; thủ tục bên thứ ba chỉ hướng dẫn theo quy định công khai
- 07/08 — thiết kế và viết `docs/architecture_diagram.md`
- 07/08 — ghim phiên bản thư viện, cài đủ dependency Phase 1 cho cả backend và frontend
- 07/08 — phân role chính thức: Hiếu (BE + Data), Hải (AI), Thu (FE)

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| **Các tài liệu của nhóm mâu thuẫn nhau** — bộ user story/schema mới bỏ hẳn tính cá nhân hóa, trong khi PRD và đề bài đều yêu cầu; PRD dùng bộ thuộc tính khác hẳn tài liệu tóm tắt bối cảnh | Đối chiếu tất cả tài liệu với **đề bài gốc**, lập PROJECT_CHARTER làm nguồn sự thật duy nhất, kèm sổ ghi quyết định phân biệt rõ "đã xác nhận" và "còn giả định" | Hết mâu thuẫn; mọi quyết định về sau đều ghi vào một chỗ |
| Nhầm lẫn về người dùng chính — tưởng là người thuê, thực tế người thuê không dùng được app Vinhomes Resident và phải làm tạm trú qua công an | Tách vấn đề theo **loại quy trình** thay vì theo loại người dùng: quy trình thuộc BQL hỗ trợ đầy đủ, quy trình bên thứ ba chỉ hướng dẫn tham khảo | Phục vụ được cả chủ hộ lẫn người thuê mà không vi phạm yêu cầu "trích nguồn, không bịa" |
| Khối lượng Phase 1 (~120h) vượt xa 5 ngày còn lại tới GATE 2 | Cắt Phase 1 thành hai lát: `[GATE 2]` bắt buộc và `[W4]` làm sau. Hoãn nhánh FAQ, giao diện upload, dashboard, PWA | Lát cắt GATE 2 vừa sức, vẫn đủ chứng minh giá trị sản phẩm |
| Cổng dữ liệu 13/08 nằm **sau** ngày demo 12/08 → có nguy cơ không có tài liệu nào để RAG truy xuất lúc demo | Dùng Thông tư 02/2016/TT-BXD (công khai, tải được ngay) làm KB cho GATE 2, gắn `source_type: public_regulation` | Không còn phụ thuộc việc BQL có hợp tác hay không |

### Bài học
- **Tài liệu do nhiều người soạn độc lập sẽ trôi lệch nhau nếu không có nguồn sự thật duy nhất.** Triệu chứng chỉ lộ ra khi ghép lại để code, lúc đó đã tốn công.
- **Đối chiếu ngược lên đề bài gốc trước khi tranh luận nội bộ.** Nhóm suýt bỏ tính cá nhân hóa — thứ mà đề bài ghi rõ trong yêu cầu Cơ bản, tức là bắt buộc chấm điểm.
- Phân biệt "đã xác nhận" và "đang giả định" trong tài liệu quan trọng không kém việc ghi lại quyết định. Một giả định cá nhân bị tưởng là quyết định của cả nhóm đã dẫn tới thiết kế sai hướng.
- Ước lượng effort phải đặt cạnh deadline mới có ý nghĩa. Kiến trúc đúng cho Phase 1 chưa chắc là thứ làm kịp trong 5 ngày.

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
- [x] Phase 2: agent tạo ticket, HITL BQL duyệt hồ sơ, định tuyến phòng ban, nhắc việc
- [x] Triển khai Railway + Vercel
- [x] Nộp hồ sơ dự án (26/08)

### Đã hoàn thành

**Backend (Hiếu)** — 10 task Phase 2, chạy bằng subagent-driven development:
- Bảng Phase 2: roles, permissions, departments, tickets, notifications, audit_log, usage_logs
- RBAC theo permission (`require_permission`), không chỉ theo vai trò
- Web Push: đăng ký thiết bị + bắn thông báo khi BQL đổi trạng thái hồ sơ
- Hệ thống ticket (US-11), duyệt hàng loạt kèm khoá lạc quan, tự phân công theo tải
- Xem tài liệu qua signed URL, theo dõi chi phí LLM, ghi nhật ký hành động

**AI (Hải)**: guardrails + node LangChain; mời cư dân gửi câu hỏi cho BQL khi KB thiếu dữ liệu.

**Frontend (Thu)**: luồng điền hồ sơ có AI dẫn dắt, nhắc việc cho cư dân, cải thiện mobile.

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Task 1-4 tạo cột trong DB nhưng quên khai trong ORM → Task 6 không chạy được | Bổ sung `Application.assigned_to`, `version`, `User.department_id`, ORM `Department`/`StaffAssignment` trước khi làm tiếp | Task 6-10 chạy suôn |
| Endpoint duyệt hàng loạt dùng `require_admin` thay vì `require_permission(BATCH_APPROVE)` | Reviewer bắt được, sửa trong một vòng | Phân quyền nhất quán toàn bộ endpoint mới |
| `update_application_status` ghi `user_id=None` vào nhật ký — không biết ai đã đổi | Thêm tham số `performed_by`, truyền từ route xuống | Nhật ký truy vết được người thực hiện |
| Truy vấn tự phân công lọc `role IN ('admin','staff')` nhưng `staff` không có trong enum `User.role` | Bỏ điều kiện thừa; `JOIN staff_assignments` đã đủ giới hạn theo bộ phận | Tự phân công hoạt động |

### Bài học
- **Cột trong migration không tự xuất hiện trong ORM.** Hai nơi phải sửa, thiếu một là hỏng ở task sau chứ không hỏng ngay — mất thời gian truy nguyên.
- **Reviewer bắt được thứ mình không thấy.** Lỗi `require_admin` và `user_id=None` đều lọt qua mắt người viết, chỉ lộ ra khi có người đọc lại với đúng bản đặc tả trong tay.

### Kế hoạch tuần sau
- Dựng hệ thống quan sát (log, chỉ số, cảnh báo)
- Hoàn thiện pitch deck và video demo
- Chạy eval lấy số liệu thật cho slide

---

## Week 6: 27/08 - 01/09 — Demo Day

### Mục tiêu tuần này
- [ ] Hoàn thiện pitch deck và video demo
- [x] Chạy eval, đưa số liệu vào slide
- [ ] Demo Day (01/09)

### Đã hoàn thành

**Hệ thống quan sát (Hiếu)** — 29-30/08:
- `AlertService`: cửa sổ trượt 5 phút + webhook Slack. Ngưỡng theo `OPERATIONS.md`
  mục 4: lỗi >1%, p95 >8s, chi phí >$10/ngày, health check hỏng 3 lần liên tiếp.
- `GET /api/v1/metrics` định dạng Prometheus; `docker-compose.yml` dựng sẵn
  backend + Prometheus + Grafana, Grafana tự nạp datasource và dashboard.
- Đã kiểm chứng chuỗi đầy đủ: backend → Prometheus → Grafana trả về số thật.

**Dọn cây migration (Hiếu)** — 28/08: cây Alembic có 3 head song song, DB dùng
chung thiếu cột `checklist_items.form_schema` khiến **mọi** request chạm
checklist trả 500 cho cả nhóm.

**Đánh giá độc lập (Hải)** — 29/08: đổi giám khảo từ gpt-4o-mini (tự chấm bài
mình) sang Claude Sonnet 5.

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| Cây Alembic 3 head, DB thiếu cột `form_schema` → cả nhóm nhận 500 | Không gộp cả 3 nhánh vì nhánh Phase 2 có `drop_table('applications')` — bảng này tạo trước điểm rẽ, gộp thẳng sẽ **xoá dữ liệu thật**. Viết migration vá riêng rồi `alembic stamp` | Về 1 head, không mất dữ liệu |
| Grafana hiện "No data" dù Prometheus có số | Dashboard trỏ datasource bằng `uid`, mà `uid` để Grafana tự sinh thì **mỗi máy một khác** — teammate dựng stack mới cũng sẽ trắng | Đặt `uid: moveinmate-prometheus` cố định trong provisioning |
| 4 test `test_alerts.py` đỏ | Tính tay lại: cả 4 sai ở **test**, không phải ở code. VD test nói "dưới 10 request" nhưng vòng lặp tạo đúng 10; test p95 dùng 1 mẫu chậm trên 51 mẫu, p95 rơi vào vị trí 48 nên vẫn là 1s | 534/534 xanh. Đã thử phá ngưỡng để chắc test bắt được lỗi thật |
| Model tự chấm bài mình (self-judge bias) | Hải tách giám khảo sang Claude Sonnet 5 | Xem mục Bài học |
| **Production chết hoàn toàn (502)** sau khi chạy migration lên Supabase dùng chung trước khi deploy code | `railway up` để build image mới có file migration. Nút "Redeploy" không cứu được — nó chạy lại image cũ, không build lại | Khôi phục sau ~20 phút; Chroma vẫn đủ 412 chunk, không mất dữ liệu |

### Bài học
- **Chỉ số tự chấm là chỉ số vô nghĩa.** Khi gpt-4o-mini vừa sinh câu trả lời
  vừa chấm điểm, kết quả là **100%** ở cả ba tiêu chí — hoàn hảo đến mức đáng
  ngờ. Đổi sang giám khảo độc lập: **48,6% đúng, 35,7% có trích dẫn**. Con số
  100% từng được coi là thành tích, thực chất chỉ là model khen chính nó.
  Khoảng cách 94,6% (khớp từ khoá) so với 48,6% (đúng nội dung) cũng cho thấy
  đo bằng từ khoá không nói lên điều gì về tính đúng đắn.
- **Test đỏ không đồng nghĩa code sai.** Cả 4 test hỏng đều do chính test tự
  mâu thuẫn với mô tả của nó. Tính tay trước khi sửa code — nếu sửa code cho
  test xanh thì đã phá đúng hành vi đang đúng.
- **Migration gộp có thể xoá dữ liệu.** `alembic merge` sinh sẵn không đọc nội
  dung `downgrade()`; nhánh Phase 2 có `drop_table('applications')` mà bảng đó
  nằm ngoài phạm vi gộp. Phải đọc từng nhánh trước khi gộp trên DB dùng chung.
- **Có migration mới thì deploy code TRƯỚC, migrate DB SAU.** Ngày 30/08 làm
  ngược lại: chạy `alembic upgrade head` từ máy cá nhân lên Supabase dùng chung
  trong khi image trên Railway chưa có file migration đó. `docker-entrypoint.sh`
  chạy `alembic upgrade head` lúc khởi động, không tra được revision, container
  thoát, Railway restart — lặp vô hạn và **API cũ cũng chết theo**, không chỉ
  tính năng mới. Trước khi chạy, tôi đã kiểm migration an toàn với *dữ liệu*
  nhưng bỏ sót câu hỏi *"code đang chạy có file này chưa"*. Kiểm đúng một nửa
  vẫn là chưa kiểm.

### Kế hoạch còn lại trước Demo Day
- **Chốt cách trình bày số liệu eval** — dùng 48,6% (trung thực, kèm giải
  thích vì sao con số cũ sai) thay vì 100%
- Backend: Report API, Settings API, Badge system (spec đã viết 29/08)
- Frontend: trang Báo cáo, Cài đặt, chuông thông báo
- AI: FAQ CRUD + tích hợp LangGraph
