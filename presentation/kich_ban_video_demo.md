# Kịch bản Video Demo — MoveInMate
**Thời lượng: tối đa 3:00** · Trọng tâm: **vận hành & giá trị sản phẩm** (không đi sâu kỹ thuật/tech stack)

---

## Chuẩn bị trước khi quay

| Việc | Chi tiết |
|---|---|
| Tài khoản cư dân đối chứng | `tran.hong.tuan1@moveinmate.demo` (chủ hộ · có xe · 10 mục) và `dang.ngoc.lan5@moveinmate.demo` (người thuê · có xe · 9 mục) — hoặc dùng cặp 6-mục (`duong.ngoc.mai3` / `pham.thi.dung4`) nếu muốn nhấn "cùng số lượng, khác nội dung" |
| Tài khoản trắng để quay onboarding | `mentor@moveinmate.demo` — **gõ tay**, chỉ dùng được **một lần**, nhớ quay thử trước để canh timing rồi mới quay bản chính thức |
| Tài khoản BQL | `bql@moveinmate.demo` |
| Mật khẩu chung | `MoveInMate!2026` |
| Câu hỏi chat nên hỏi trước | 1 câu **có** trong KB (để show trích nguồn) + 1 câu **ngoài phạm vi** (để show từ chối, ví dụ hỏi về sửa xe/mua bán căn hộ) |
| Ghi màn hình | Ưu tiên 1080p, tốc độ chuột chậm rãi, không di chuột thừa — mỗi cảnh giữ ổn định vài giây trước khi chuyển |

---

## Kịch bản theo timecode

| TC | Hình ảnh trên màn hình | Lời thoại (VO) | Chữ trên màn hình (OST) |
|---|---|---|---|
| **0:00–0:15** | Mở bằng vài dòng chữ trên nền tối (không cần quay màn hình): hình ảnh checklist giấy lộn xộn, hoặc liệt kê nhanh các thủ tục (thẻ cư dân, thẻ xe, internet, nội quy, tiện ích) | "Mỗi cư dân mới nhận nhà phải tự mò hàng chục thủ tục — không ai đưa cho họ một danh sách đúng với hoàn cảnh của mình. Kết quả: cư dân bỏ sót việc, còn Ban quản lý mỗi ngày trả lời hàng trăm câu hỏi giống nhau." | **Vấn đề: thủ tục rời rạc, không ai hướng dẫn theo đúng hoàn cảnh** |
| **0:15–0:30** | Logo/tên sản phẩm MoveInMate xuất hiện, sau đó cắt sang màn hình đăng nhập | "MoveInMate là trợ lý AI giúp cư dân mới của Vinhomes Smart City biết chính xác mình cần làm gì — và giúp Ban quản lý biết ai đang tắc ở đâu để hỗ trợ trước khi bị phàn nàn." | **MoveInMate — checklist cá nhân hoá + trợ lý thủ tục có trích nguồn** |
| **0:30–1:05** | Đăng nhập bằng `mentor@…` → điền form onboarding 4 câu hỏi (chủ hộ/người thuê, loại căn, có xe, gói tiện ích) → checklist hiện ra | "Cư dân chỉ cần trả lời 4 câu hỏi. Không dùng chatbot đoán mò — một rule engine tất định sinh ra đúng checklist cho hoàn cảnh của họ, có cả tiến độ hoàn thành." | **4 câu hỏi → checklist cá nhân hoá tức thì** |
| **1:05–1:25** | Cắt nhanh sang so sánh 2 tài khoản: chủ hộ và người thuê cùng có "xe" — đặt 2 checklist cạnh nhau (ghi màn hình lần lượt rồi dựng song song, hoặc chia đôi màn hình khi edit) | "Đây là điểm khác biệt: hai hộ có cùng số mục trong checklist, nhưng nội dung hoàn toàn khác nhau — chủ hộ được nhắc cập nhật thông tin cư trú, người thuê được nhắc đăng ký tạm trú tại công an phường. Cá nhân hoá nằm ở nội dung, không phải ở số lượng." | **Cá nhân hoá thật: cùng số mục, khác nội dung** |
| **1:25–1:55** | Mở khung chat, gõ 1 câu hỏi thủ tục thật → trả lời hiện ra kèm thẻ nguồn trích dẫn → sau đó gõ 1 câu hỏi ngoài phạm vi → hệ thống từ chối trả lời | "Mỗi câu trả lời đều kèm nguồn trích dẫn lấy trực tiếp từ tài liệu dự án — không phải do AI tự bịa. Và khi không có căn cứ, hệ thống chủ động từ chối thay vì đoán — cơ chế này nằm trong code, không phải chỉ dặn dò trong prompt." | **Trả lời có nguồn — hoặc từ chối, không bao giờ bịa** |
| **1:55–2:35** | Đăng xuất, đăng nhập `bql@…` → dashboard tổng quan tiến độ tất cả cư dân → click vào 1 cư dân xem chi tiết hồ sơ đã nộp → cảnh ngắn thao tác khoá/mở tài khoản hoặc reset mật khẩu → cảnh ngắn màn hình nạp tài liệu mới vào kho tri thức (trạng thái "đang nạp… hoàn tất") | "Về phía vận hành: Ban quản lý thấy toàn cảnh tiến độ mọi cư dân trên một màn hình, không cần hỏi từng người. Họ có thể xem chi tiết hồ sơ đã nộp, khoá tài khoản hoặc cấp lại mật khẩu khi cần, và tự nạp thêm tài liệu mới vào hệ thống mà không cần đội kỹ thuật can thiệp. Toàn bộ được bảo vệ bằng giới hạn tần suất và kiểm tra sức khoẻ hệ thống, để một lượt truy cập bất thường không làm sập trợ lý cho tất cả mọi người." | **Ban quản lý: một màn hình thấy toàn bộ, tự vận hành, không cần chờ kỹ thuật** |
| **2:35–2:55** | Cắt sang slide tóm tắt số liệu (dựng đồ hoạ đơn giản, không cần quay màn hình): "32/35 câu trả lời đúng (91%)", "giảm số lượt hỏi lặp lại cho BQL", "4–10 mục checklist tuỳ hoàn cảnh" | "Trên bộ 35 câu hỏi đánh giá, trợ lý trả lời đúng 91%. Với Ban quản lý, đây là ít cuộc gọi hỏi lại hơn, ít sai sót hồ sơ hơn — và cư dân mới có một điểm bắt đầu rõ ràng thay vì tự mò trong 4 đến 6 tuần đầu." | **91% câu trả lời đúng · vận hành nhẹ hơn cho Ban quản lý** |
| **2:55–3:00** | Logo MoveInMate + tên team | "MoveInMate — mỗi hộ một danh sách đúng của riêng mình." | **MoveInMate** |

**Tổng thời lượng: 3:00**

---

## Ghi chú dựng phim

- Cảnh **1:05–1:25** (so sánh chủ hộ/người thuê) là khoảnh khắc "aha" quan trọng nhất — nên dựng chia đôi màn hình hoặc chuyển cảnh nhanh, đừng để loãng.
- Cảnh từ chối (1:25–1:55) chỉ cần 3–4 giây, không cần đọc hết câu trả lời từ chối — mục đích là cho thấy hệ thống *có* cơ chế này.
- Đừng quay cảnh nạp tài liệu KB kéo dài quá 5 giây — trạng thái `embed_status` chạy nền, chỉ cần thấy nó chuyển từ "đang xử lý" sang "hoàn tất" là đủ.
- Nếu thời gian dựng eo hẹp, có thể bỏ đoạn khoá/mở tài khoản và dồn thời lượng cho phần dashboard tiến độ — đó là phần thể hiện giá trị vận hành rõ nhất.
- Nhạc nền: chọn tông nhẹ, không lời, giảm âm lượng khi có voiceover.
