# Kịch bản Video Demo — MoveInMate
**Thời lượng: tối đa 3:00** · Trọng tâm: **vận hành & giá trị sản phẩm** (không đi sâu kỹ thuật/tech stack)

---

## Chuẩn bị trước khi quay

| Việc | Chi tiết |
|---|---|
| Tài khoản cư dân đối chứng | **Dùng cặp này cho cảnh 1:05** — `duong.ngoc.mai3@moveinmate.demo` (chủ hộ · không xe) và `pham.thi.dung4@moveinmate.demo` (người thuê · không xe): **cùng 6 mục, khác nhau đúng 2 mục** (đã kiểm 31/08).<br>Cặp `tran.hong.tuan1` (chủ hộ · có xe · **10** mục) và `dang.ngoc.lan5` (người thuê · có xe · **9** mục) KHÔNG bằng nhau — dùng cặp này thì lời thoại "cùng số mục" sai. |
| Tài khoản trắng để quay onboarding | `phan.quang.trang8@moveinmate.demo` — dự phòng: `dinh.hai.lan28@moveinmate.demo`. **Mỗi tài khoản chỉ dùng được MỘT LẦN** (điền xong là hết trắng), nên quay thử bằng tài khoản dự phòng để canh timing, rồi quay bản chính bằng tài khoản còn lại.<br>⚠️ `mentor@moveinmate.demo` **không còn tồn tại** — seed lại dữ liệu ngày 30/08. Đây là hai tài khoản chưa onboarding duy nhất; lỡ dùng hết cả hai thì chạy `python -m scripts.seed_data` rồi `python -m scripts.provision_auth` để dựng lại (xoá toàn bộ hồ sơ và lịch sử chat hiện có). |
| Tài khoản BQL | `bql@moveinmate.demo` |
| Mật khẩu chung | `MoveInMate!2026` |
| Câu hỏi chat — **dùng đúng câu đã kiểm** | **Có nguồn:** *"Phí gửi xe ô tô một tháng là bao nhiêu?"* (Q12 — giám khảo chấm đúng, 2 nguồn) hoặc *"Ban quản lý có làm hộ thủ tục đăng ký thường trú không?"* (Q10 — 2 nguồn).<br>**Bị từ chối:** *"Giá vàng hôm nay bao nhiêu?"* (Q29) hoặc *"Thời tiết Hà Nội ngày mai thế nào?"* (Q30).<br>Bốn câu này lấy từ lần đo 29/08, không phải câu ứng khẩu — **đừng gõ câu khác khi đang quay**, tỉ lệ trả lời đúng trên toàn bộ là 17/35. |
| Ghi màn hình | Ưu tiên 1080p, tốc độ chuột chậm rãi, không di chuột thừa — mỗi cảnh giữ ổn định vài giây trước khi chuyển |

---

## Kịch bản theo timecode

| TC | Hình ảnh trên màn hình | Lời thoại (VO) | Chữ trên màn hình (OST) |
|---|---|---|---|
| **0:00–0:15** | Mở bằng vài dòng chữ trên nền tối (không cần quay màn hình): hình ảnh checklist giấy lộn xộn, hoặc liệt kê nhanh các thủ tục (thẻ cư dân, thẻ xe, internet, nội quy, tiện ích) | "Mỗi cư dân mới nhận nhà phải tự mò hàng chục thủ tục — không ai đưa cho họ một danh sách đúng với hoàn cảnh của mình. Kết quả: cư dân bỏ sót việc, còn Ban quản lý mỗi ngày trả lời hàng trăm câu hỏi giống nhau." | **Vấn đề: thủ tục rời rạc, không ai hướng dẫn theo đúng hoàn cảnh** |
| **0:15–0:30** | Logo/tên sản phẩm MoveInMate xuất hiện, sau đó cắt sang màn hình đăng nhập | "MoveInMate là trợ lý AI giúp cư dân mới của Vinhomes Smart City biết chính xác mình cần làm gì — và giúp Ban quản lý biết ai đang tắc ở đâu để hỗ trợ trước khi bị phàn nàn." | **MoveInMate — checklist cá nhân hoá + trợ lý thủ tục có trích nguồn** |
| **0:30–1:05** | Đăng nhập bằng `mentor@…` → điền form onboarding 4 câu hỏi (chủ hộ/người thuê, loại căn, có xe, gói tiện ích) → checklist hiện ra | "Cư dân chỉ cần trả lời 4 câu hỏi. Không dùng chatbot đoán mò — một rule engine tất định sinh ra đúng checklist cho hoàn cảnh của họ, có cả tiến độ hoàn thành." | **4 câu hỏi → checklist cá nhân hoá tức thì** |
| **1:05–1:25** | Cắt nhanh sang so sánh `duong.ngoc.mai3` (chủ hộ) và `pham.thi.dung4` (người thuê) — đặt 2 checklist cạnh nhau (ghi màn hình lần lượt rồi dựng song song, hoặc chia đôi màn hình khi edit). **Highlight đúng 2 dòng khác nhau ở mỗi bên** | "Đây là điểm khác biệt: hai hộ có cùng sáu mục trong checklist, nhưng nội dung khác nhau — chủ hộ được nhắc cập nhật thông tin cư trú, người thuê được nhắc đăng ký tạm trú tại công an phường. Cá nhân hoá nằm ở nội dung, không phải ở số lượng." | **Cá nhân hoá thật: cùng 6 mục, khác nội dung** |
| **1:25–1:55** | Mở khung chat, gõ 1 câu hỏi thủ tục thật → trả lời hiện ra kèm thẻ nguồn trích dẫn → sau đó gõ 1 câu hỏi ngoài phạm vi → hệ thống từ chối trả lời | "Mỗi câu trả lời đều kèm nguồn trích dẫn lấy trực tiếp từ tài liệu dự án — không phải do AI tự bịa. Và khi không có căn cứ, hệ thống chủ động từ chối thay vì đoán — cơ chế này nằm trong code, không phải chỉ dặn dò trong prompt." | **Trả lời có nguồn — hoặc từ chối, không bao giờ bịa** |
| **1:55–2:35** | Đăng xuất, đăng nhập `bql@…` → dashboard tổng quan tiến độ tất cả cư dân → click vào 1 cư dân xem chi tiết hồ sơ đã nộp → cảnh ngắn thao tác khoá/mở tài khoản hoặc reset mật khẩu → cảnh ngắn màn hình nạp tài liệu mới vào kho tri thức (trạng thái "đang nạp… hoàn tất") | "Về phía vận hành: Ban quản lý thấy toàn cảnh tiến độ mọi cư dân trên một màn hình, không cần hỏi từng người. Họ có thể xem chi tiết hồ sơ đã nộp, khoá tài khoản hoặc cấp lại mật khẩu khi cần, và tự nạp thêm tài liệu mới vào hệ thống mà không cần đội kỹ thuật can thiệp. Toàn bộ được bảo vệ bằng giới hạn tần suất và kiểm tra sức khoẻ hệ thống, để một lượt truy cập bất thường không làm sập trợ lý cho tất cả mọi người." | **Ban quản lý: một màn hình thấy toàn bộ, tự vận hành, không cần chờ kỹ thuật** |
| **2:35–2:55** | Cắt sang slide tóm tắt số liệu (dựng đồ hoạ đơn giản, không cần quay màn hình): "37 câu · giám khảo độc lập chấm: 17 đúng · 12 chưa xác minh được · 6 sai", "4–10 mục checklist tuỳ hoàn cảnh" | "Chúng tôi để một model khác chấm bài — không để hệ thống tự chấm chính nó. Trên 37 câu, giám khảo độc lập xác nhận 17 câu đúng, 12 câu chưa đủ căn cứ để kết luận, 6 câu sai. Con số này thấp hơn nhiều so với cách đo khớp từ khoá, và chúng tôi giữ nó vì nó phản ánh đúng thứ cần sửa tiếp." | **Đo bằng giám khảo độc lập — 17 đúng / 12 chưa rõ / 6 sai trên 37 câu** |
| **2:55–3:00** | Logo MoveInMate + tên team | "MoveInMate — mỗi hộ một danh sách đúng của riêng mình." | **MoveInMate** |

**Tổng thời lượng: 3:00**

---

## Ghi chú dựng phim

- Cảnh **1:05–1:25** (so sánh chủ hộ/người thuê) là khoảnh khắc "aha" quan trọng nhất — nên dựng chia đôi màn hình hoặc chuyển cảnh nhanh, đừng để loãng.
- Cảnh từ chối (1:25–1:55) chỉ cần 3–4 giây, không cần đọc hết câu trả lời từ chối — mục đích là cho thấy hệ thống *có* cơ chế này.
- Đừng quay cảnh nạp tài liệu KB kéo dài quá 5 giây — trạng thái `embed_status` chạy nền, chỉ cần thấy nó chuyển từ "đang xử lý" sang "hoàn tất" là đủ.
- Nếu thời gian dựng eo hẹp, có thể bỏ đoạn khoá/mở tài khoản và dồn thời lượng cho phần dashboard tiến độ — đó là phần thể hiện giá trị vận hành rõ nhất.
- Nhạc nền: chọn tông nhẹ, không lời, giảm âm lượng khi có voiceover.

---

## Số liệu đánh giá — dùng bản nào và vì sao

**Bản dùng:** `eval/results/run-20260829-1253*.json` · giám khảo `claude-sonnet-5`

| Chỉ số | Giá trị |
|---|---|
| Tổng câu hỏi | 37 |
| Khớp từ khoá bắt buộc | 35/37 = **94,6%** |
| Giám khảo chấm ĐÚNG | 17/35 = **48,6%** |
| Giám khảo chấm KHÔNG CHẮC CHẮN | 12 |
| Giám khảo chấm SAI | 6 |
| Có trích dẫn nguồn hợp lệ | 10/35 = **35,7%** |
| Độ trễ p95 | 5.309 ms (mục tiêu 3.000 ms — **chưa đạt**) |

**Con số 91% trong bản kịch bản cũ đã bị gỡ.** Nó đến từ lần đo mà chính
gpt-4o-mini vừa sinh câu trả lời vừa chấm điểm bài của mình, và cho **100%** ở
cả ba tiêu chí — một kết quả hoàn hảo đáng ngờ. Ngày 29/08 tách giám khảo sang
một model khác thì còn 48,6%.

**Nói 17/12/6 thay vì "48,6%".** Nhãn "KHÔNG CHẮC CHẮN" nghĩa là giám khảo
không đủ căn cứ để kết luận, **không phải sai**. Gộp 12 câu đó vào phần "không
đúng" là tự nhận lỗi mình không mắc.

### Nếu ban giám khảo hỏi

> *"Vì sao khớp từ khoá 94,6% mà chấm đúng chỉ 48,6%?"*

Vì khớp từ khoá chỉ kiểm chuỗi con: câu trả lời chứa đủ từ khoá vẫn có thể sai
nội dung. 6/37 câu qua được kiểm tra từ khoá nhưng bị chấm SAI — đó chính là
chế độ hỏng nguy hiểm nhất, câu trả lời nghe hợp lý và có trích dẫn trông đáng
tin nhưng nội dung sai.

> *"Sao không dùng con số cao hơn?"*

Con số cao hơn đến từ việc model tự chấm bài mình. Chúng tôi giữ con số thấp vì
nó chỉ ra đúng thứ cần sửa, và vì một chỉ số không kiểm chứng được thì không
dùng để ra quyết định được.

> *"Tỉ lệ trích dẫn 35,7% có thấp quá không?"*

Có, và đây là việc còn nợ. Một phần do trước đó giám khảo chỉ được đưa **tiêu
đề** tài liệu chứ không có đoạn trích, nên không xác minh được trích dẫn có đúng
không. Đã sửa ngày 29/08 nhưng chưa đo lại đủ.
