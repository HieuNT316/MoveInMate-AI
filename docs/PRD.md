# PRD — MoveInMate

**Cập nhật:** 11/08/2026 · **Trạng thái:** Phase 1, trước GATE 2

## Quan hệ với tài liệu khác — đọc trước

Tài liệu này **chỉ nói về trải nghiệm sản phẩm**: người dùng thấy gì, làm gì, cảm giác ra sao. Nó **không** định nghĩa phạm vi, quyết định hay dữ liệu — những thứ đó nằm ở nơi khác và nếu mâu thuẫn thì **nơi khác thắng**:

| Câu hỏi | Đọc ở đâu |
|---|---|
| Phạm vi, user story, quyết định đã chốt, timeline | `PROJECT_CHARTER.md` — **nguồn sự thật duy nhất** |
| Thiết kế kỹ thuật, hợp đồng API, luồng dữ liệu | `architecture_diagram.md` |
| Ai làm gì, khi nào | `ROLES_AND_PLAN.md` |

Lý do có quy tắc này: tháng 8/2026 nhóm đã một lần để user story, schema và luồng UI trôi lệch nhau thành ba mô tả sản phẩm khác nhau. PRD là tài liệu dễ trôi nhất vì ai cũng thấy mình có ý kiến về UX.

## 1. Sản phẩm giải quyết gì

Cư dân mới nhận căn hộ phải hoàn thành hàng chục thủ tục rời rạc — thẻ cư dân, thẻ xe, tạm trú, tiện ích — mỗi thủ tục một nơi nộp, một bộ giấy tờ, một thời hạn. Không ai đưa cho họ một danh sách đúng với hoàn cảnh của mình, nên họ hỏi đi hỏi lại Ban quản lý những câu giống nhau, và vẫn bỏ sót.

MoveInMate đưa cho mỗi hộ **đúng danh sách của họ**, kèm trợ lý trả lời thủ tục có trích nguồn.

**Người mua là Ban quản lý.** Cư dân là người dùng cuối, được BQL cấp tài khoản. Mọi quyết định thiết kế khi phải chọn đều nghiêng về tín hiệu vận hành sạch cho BQL.

## 2. Người dùng

| Persona | Là ai | Cần gì nhất |
|---|---|---|
| **Chủ hộ** (chính) | Vừa nhận bàn giao căn hộ | Biết mình phải làm gì, theo thứ tự nào |
| **Người thuê** (nhánh phụ) | Thuê lại từ chủ hộ | Danh sách khác chủ hộ: cần uỷ quyền, phải đăng ký tạm trú |
| **Ban quản lý** | Vận hành toà nhà | Thấy hộ nào đang tắc ở đâu để hỗ trợ trước khi bị phàn nàn |

## 3. Hành trình chính

### 3.1 Cư dân — từ đăng nhập tới hoàn thành

1. **Đăng nhập** bằng tài khoản BQL cấp. Không có đăng ký công khai.
2. **Trả lời 4 câu hỏi** (hình thức sở hữu, loại căn, có xe, gói tiện ích). Không hỏi những gì không dùng để lọc.
3. **Nhận checklist của riêng mình** — 4 đến 10 mục tuỳ hoàn cảnh, kèm tiến độ.
4. **Hỏi trợ lý** bất cứ lúc nào; câu trả lời luôn kèm nguồn, hoặc từ chối.
5. **Tick khi xong**; sửa hồ sơ thì danh sách tự cập nhật ngay.

### 3.2 Ban quản lý

Đăng nhập → bảng tiến độ toàn bộ cư dân, **chỉ tính thủ tục BQL thật sự xử lý được**. Không tính tạm trú (công an phường) vào tín hiệu vận hành của họ.

## 4. Nguyên tắc trải nghiệm

Bốn nguyên tắc dưới đây có thứ tự ưu tiên. Khi mâu thuẫn, cái trên thắng.

### 4.1 Thà nói không biết còn hơn hướng dẫn sai

Thủ tục hành chính sai khiến người ta đi lại lần hai. Trợ lý từ chối khi không có căn cứ, và **cơ chế từ chối nằm trong code, không phải trong prompt**.

### 4.2 Minh bạch nguồn — kể cả khi nguồn là dữ liệu mô phỏng

Mỗi câu trả lời hiện nguồn kèm nhãn phân loại. Dữ liệu nhóm tự dựng cho demo mang nhãn **"Quy trình mô phỏng (dữ liệu demo)"**, không giấu.

Nói trước là minh bạch; bị hỏi mới nói là bị bắt lỗi.

### 4.3 Gỡ sự mơ hồ trước, tạo động lực sau

Người dùng ngại làm thủ tục **không phải vì thiếu động lực mà vì thiếu thông tin**: không biết mang gì, mất bao lâu, đi đâu, có phải quay lại lần hai không.

Vì vậy mỗi mục checklist phải trả lời được ba câu trước khi nghĩ tới phần thưởng:

- **Mang gì?** — danh mục giấy tờ cụ thể
- **Bao lâu?** — thời hạn xử lý theo ngày làm việc
- **Ở đâu, ai xử lý?** — điểm nộp và bộ phận phụ trách

Lớp phần thưởng (huy hiệu, trang trí hồ sơ) đứng **sau** ba câu này, không thay thế chúng.

### 4.4 Không hứa thay mặt Ban quản lý

Phần thưởng phải là thứ sản phẩm tự trao được: huy hiệu, cột mốc, trang trí hồ sơ. **Không hứa ưu đãi tiền** kiểu "làm thẻ xe được giảm phí gửi xe" — đó là tiền của BQL, sản phẩm không có quyền hứa, và người mua nhận ra ngay.

## 5. Tính năng

### 5.1 Đã có (GATE 2)

| Tính năng | Người dùng thấy gì |
|---|---|
| Đăng nhập | Chọn tài khoản, vào thẳng dashboard hoặc form onboarding nếu chưa khai |
| Form onboarding | 4 câu hỏi, multi-select cho gói tiện ích |
| Checklist cá nhân hoá | Danh sách theo hoàn cảnh; mục ngoài phạm vi BQL có nhãn riêng |
| Hai con số tiến độ | "Tiến độ chung" cho cư dân, "Thủ tục qua BQL" cho BQL |
| Sửa hồ sơ | Đổi một trường, checklist cập nhật ngay lập tức |
| Trợ lý hỏi đáp | Trả lời kèm thẻ nguồn có nhãn phân loại, hoặc từ chối |
| Dashboard BQL | Bảng cư dân kèm thanh tiến độ |

### 5.2 Đang làm dở — cần hoàn thiện để tính là tính năng

| Tính năng | Trạng thái thật | Thiếu gì |
|---|---|---|
| **Điều hướng nộp hồ sơ** | BE trả `suggested_action`; **FE chưa khai báo type nên đang bỏ qua hoàn toàn** | FE hiện nút; trang đích; lớp đối chiếu tất định ở BE (tool LLM mới bắn 2/4 cách hỏi) |
| **Form nộp hồ sơ online** | FE đang làm | Chưa có contract API viết ra giữa FE và BE — **phải chốt trước khi code song song** |

### 5.3 Xếp W4 — góp ý mentor 08/08, không bắt buộc cho GATE 2

| Tính năng | Ghi chú |
|---|---|
| "Mang gì / bao lâu / ở đâu" trên mỗi mục checklist | Dữ liệu **đã có sẵn** trong `data/kb/bql/`, chỉ cần đưa lên schema và UI. Giá trị cao nhất trong nhóm này |
| Huy hiệu khi hoàn thành thủ tục | Hiện ngay tại chỗ tick, không cần trang riêng |
| Câu trả lời chat có cấu trúc | Bước đánh số, tách khối "giấy tờ / thời gian / địa điểm" thành card |
| Hình minh hoạ trong chat | **Không cào được ảnh trang nguồn** (placeholder lazy-load, và là ảnh bên thứ ba). Hướng khả thi: 4-5 ảnh theo `category` |

### 5.4 Không làm

Đa ngôn ngữ · OCR xác thực giấy tờ · thông báo email/SMS/Zalo · analytics nâng cao · đồng bộ dữ liệu offline (PWA chỉ là vỏ cài đặt được).

## 6. Ràng buộc ảnh hưởng tới trải nghiệm

- **Hội thoại single-turn ở Phase 1.** Hỏi nối tiếp kiểu "còn thẻ xe thì sao?" sẽ mất ngữ cảnh. Kịch bản demo phải hỏi trọn câu.
- **Đăng nhập hiện chưa kiểm mật khẩu** — tra theo email để demo nhiều persona. Tuyệt đối không lên production.
- **Ba mục checklist chưa có tài liệu BQL thật**; đang dùng dữ liệu mô phỏng có nhãn.

## 7. Đo cái gì

| Chỉ số | Vì sao | Trạng thái |
|---|---|---|
| % cư dân hoàn thành onboarding trong X ngày đầu | Giá trị chính với BQL | Có mốc `onboarding_completed_at`, chưa có báo cáo |
| Retrieval accuracy | Chất lượng trợ lý | Mục tiêu ≥7/10, **chưa đo trên bộ đủ lớn** |
| Tỷ lệ câu bị từ chối | Từ chối quá nhiều = KB thiếu; quá ít = guard hỏng | Chưa đo |
