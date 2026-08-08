# Kịch bản đọc — Báo cáo mentor 08/08

**Tổng 10 phút.** Chữ thường là lời nói. Dòng `▸` là thao tác, không đọc.

> **Chuẩn bị trước khi vào phòng:** mở sẵn 2 terminal đã chạy `uvicorn` và `npm run dev`,
> trình duyệt đã ở trang `localhost:3000/login`. Chạy trước `alembic upgrade head`
> và `python -m scripts.seed_data`. Thử lại bước 5 một lần cho chắc.

---

## Phần 1 — Mở đầu (30 giây)

Em chào thầy/cô. Em là Hiếu, nhóm P-225, dự án MoveInMate — trợ lý AI hỗ trợ cư dân làm thủ tục nhận nhà ở Vinhomes Smart City.

Em xin báo cáo phần việc từ GATE 1 ngày 5/8 đến hôm nay.

Tóm tắt trong một câu: ba ngày qua nhóm em đưa dự án từ ý tưởng còn rời rạc thành một hệ thống chạy được từ đầu đến cuối. Nhưng hai hạng mục nặng nhất là xác thực và RAG thì chưa bắt đầu. Em sẽ nói rõ cả hai mặt.

---

## Phần 2 — Đối chiếu roadmap (1 phút 30)

Theo roadmap, lát cắt bắt buộc cho GATE 2 ngày 12/8 có bảy hạng mục. Hiện tại **năm hạng mục đã xong**: cấp tài khoản cư dân, form onboarding, phân loại rule-based, checklist cá nhân hóa, tiến độ, xem sửa hồ sơ.

**Hai hạng mục chưa bắt đầu là xác thực Supabase và RAG.** Đây đúng là hai phần nặng nhất, khoảng 12 tiếng và 30 tiếng.

Về những gì làm được, em chia ba nhóm.

**Thứ nhất là định hướng.** Ngày 7/8 nhóm em phát hiện một vấn đề khá nghiêm trọng: ba người viết tài liệu độc lập nên user story, schema và luồng UI đang mô tả ba sản phẩm hơi khác nhau. Nhóm em dừng lại, lập một Project Charter làm nguồn sự thật duy nhất, và đặt quy tắc phải chốt hợp đồng bằng văn bản trước khi code. Từ đó chốt được hơn mười lăm quyết định trước đây còn mơ hồ.

**Thứ hai là dữ liệu.** Theo kế hoạch, cổng dữ liệu là ngày 13/8, tức là sau ngày demo 12/8. Nhóm em không đợi. Hôm nay đã thu thập xong khoảng **một trăm lẻ bảy nghìn token**, tương đương gần ba trăm đoạn văn bản, từ bảy trang thủ tục của Vinhomes Smart City cộng với Quy chế quản lý nhà chung cư. Hai script cào tự động, chạy lại được bất cứ lúc nào.

Trong lúc làm phần này em phát hiện một chuyện đáng lưu ý. Kế hoạch ban đầu định dùng Thông tư 02/2016. Em kiểm tra lại thì văn bản đó **đã hết hiệu lực từ tháng 8 năm 2024**, bị thay bởi Thông tư 05/2024 theo Luật Nhà ở 2023. Sản phẩm của nhóm em lấy việc trích nguồn làm giá trị cốt lõi, nên nạp một văn bản hết hiệu lực sẽ tạo ra câu trả lời sai kèm trích dẫn trông rất đáng tin. Em đã đổi sang văn bản hiện hành.

**Thứ ba là code.** Đã có sáu bảng dữ liệu với migration, bốn mươi cư dân giả, mười hai đầu việc checklist, mười hai endpoint API, chín trang giao diện đã nối API thật. Năm mươi hai bài test đều pass, CI xanh.

Em xin demo phần đang chạy được.

---

## Phần 3 — Demo (4 phút 30)

▸ *Mở `localhost:3000/login`*

Đây là màn đăng nhập. Tài khoản do Ban quản lý cấp, cư dân không tự đăng ký được — đây là quyết định nhóm em chốt sau khi tìm hiểu cách app Vinhomes Resident đang vận hành.

Phía dưới là các tài khoản mẫu. Thầy/cô để ý con số bên phải mỗi dòng: đó là **số đầu việc mà hệ thống sinh ra cho riêng hồ sơ đó**. Chưa bấm vào đã thấy khác nhau rồi.

▸ *Bấm tài khoản "Chủ hộ · 2PN · có ô tô · pool, gym"*

Đây là chủ hộ, có ô tô, đăng ký gói hồ bơi và gym. Hệ thống sinh ra **mười đầu việc**: ký nội quy, làm thẻ cư dân dành cho chủ hộ, cập nhật thông tin cư trú, đăng ký thẻ xe, chỗ đỗ xe, kích hoạt thẻ hồ bơi, thẻ gym, và các thủ tục chung.

▸ *Bấm nút "Thuê +xe" trên thanh Demo ở header*

Đổi sang người thuê có xe. Còn **chín việc**. Khác ở chỗ: hồ sơ làm thẻ cư dân là hồ sơ dành cho người thuê, cần thêm hợp đồng thuê nhà và giấy ủy quyền. Và thay vì cập nhật cư trú thì là đăng ký tạm trú tại công an phường.

▸ *Bấm nút "Chủ hộ · 6"*

Đây là chỗ em muốn nhấn mạnh nhất. Chủ hộ căn studio, không xe, không gói tiện ích: **sáu việc**.

▸ *Bấm nút "Thuê · 6"*

Người thuê, không xe, không tiện ích: **cũng sáu việc**.

Nhìn con số thì tưởng giống hệt nhau. Nhưng mở ra thì nội dung khác: một bên là thẻ cư dân chủ hộ và cập nhật thường trú, một bên là thẻ cư dân người thuê và đăng ký tạm trú. Nghĩa là hệ thống **không phải một checklist tĩnh có ẩn hiện vài dòng**, mà thực sự phân nhánh theo hoàn cảnh từng hộ.

▸ *Vào trang Hồ sơ, bấm "Đổi" ở dòng "Có xe"*

Bây giờ giả sử cư dân này vừa mua ô tô. Em đổi một trường duy nhất trong hồ sơ.

▸ *Quay lại trang Checklist*

Checklist tự lên **tám việc**, thêm đăng ký thẻ xe và chỗ đỗ xe. Tiến độ tụt từ năm mươi phần trăm xuống ba mươi bảy, vì mẫu số tăng.

Điểm kỹ thuật ở đây là nhóm em **không chốt cứng checklist lúc đăng ký**, mà lọc lại mỗi lần xem. Nhờ vậy khi Ban quản lý cập nhật thủ tục thì cư dân cũ thấy ngay, không cần đồng bộ gì cả.

▸ *Vào trang Chat, hỏi "làm thẻ xe cần giấy tờ gì"*

Phần hỏi đáp. Câu trả lời luôn kèm nguồn tài liệu ở dưới.

▸ *Hỏi tiếp "thời tiết Hà Nội hôm nay thế nào"*

Còn câu ngoài phạm vi thì hệ thống **từ chối trả lời** thay vì bịa ra. Đây là ràng buộc nhóm em đặt từ đầu: thà nói không biết còn hơn hướng dẫn sai thủ tục hành chính.

**Em xin nói rõ: hai bước hỏi đáp vừa rồi đang chạy trên dữ liệu mẫu, chưa phải RAG thật.** Dữ liệu thì đã sẵn sàng, phần embed và LangGraph bạn phụ trách AI bắt đầu từ ngày mai.

▸ *Đăng xuất, đăng nhập tài khoản Ban quản lý*

Cuối cùng là màn của Ban quản lý: danh sách bốn mươi cư dân kèm tiến độ.

Một chi tiết nhỏ nhưng nhóm em cân nhắc khá lâu: tiến độ ở đây **chỉ tính những thủ tục Ban quản lý thật sự xử lý được**. Việc như đăng ký tạm trú là do công an phường làm, Ban quản lý không giúp được và cũng không xác nhận được, nên nếu gộp chung thì họ sẽ thấy cư dân "chậm" vì một việc ngoài tầm tay mình.

---

## Phần 4 — Đang vướng và kế hoạch (1 phút 30)

Em xin nói phần chưa được.

**Thứ nhất, nhóm em chưa tạo project Supabase.** Đây là việc của em, đã trễ một ngày, và nó chặn cả phần xác thực lẫn một phần việc của bạn front-end. Em làm ngay tối nay.

**Thứ hai, RAG chưa bắt đầu.** Đây là hạng mục nặng nhất và cũng là phần "AI" mà đề bài chấm. Dữ liệu đã xong nên bạn phụ trách AI không bị chặn nữa, bắt đầu từ 9/8.

**Thứ ba, đăng nhập hiện tại chưa kiểm mật khẩu** — chỉ tra theo email để demo được nhiều hồ sơ. Phần này sẽ bỏ khi có Supabase Auth.

Ngoài ra còn ba đầu việc trong checklist mà chưa có tài liệu nguồn: ký nội quy, chỗ đỗ xe cố định, đăng ký chuyển đồ. Không trang công khai nào có, phải xin Ban quản lý hoặc bỏ khỏi danh sách.

Kế hoạch bốn ngày tới: ngày mai em làm Supabase và xác thực, bạn AI chunk và embed, bạn front-end làm form onboarding. Ngày 10 dựng LangGraph. Ngày 11 tích hợp và deploy. Ngày 12 tổng duyệt.

Nhóm em đặt một chốt chặn: **bạn AI phải đạt tối thiểu bảy trên mười câu truy xuất đúng trước khi viết node LangGraph.** Không đạt thì quay lại sửa chunking, không đi tiếp.

---

## Phần 5 — Câu hỏi (2 phút)

Em có mấy điểm muốn xin ý kiến. Em có ghi đầy đủ tám câu trong file báo cáo, ở đây em xin hỏi ba câu quan trọng nhất.

**Câu thứ nhất.** Nhóm em cố ý **không dùng LLM** cho phần phân loại và sinh checklist, mà dùng rule-based. Lý do là thủ tục hành chính cần đúng tuyệt đối và phải giải thích được tại sao ra kết quả đó — dùng LLM chỉ thêm rủi ro sai. LangGraph nhóm em chỉ dùng cho nhánh hỏi đáp. Thầy/cô cho em hỏi cách chia này có bị đánh giá là **chưa đủ hàm lượng AI** khi chấm không ạ?

**Câu thứ hai.** Khoảng bốn mươi phần trăm dữ liệu hiện tại đến từ một trang thông tin cộng đồng, **không phải trang chính thức của Ban quản lý**. Nhóm em đã gắn nhãn nguồn không chính thức cho từng tài liệu. Nếu đến ngày 13/8 Ban quản lý không cung cấp tài liệu thật, thì demo bằng nguồn này có bị trừ điểm không, và nhóm em nên hiển thị cảnh báo cho người dùng thế nào cho đúng ạ?

**Câu thứ ba.** Còn bốn ngày tới GATE 2 mà hai hạng mục nặng nhất chưa bắt đầu. Nếu buộc phải hy sinh một thứ, thầy/cô khuyên nhóm em nên giữ cái nào — **xác thực thật hay RAG thật**? Bọn em đang nghiêng về giữ RAG và tạm chấp nhận đăng nhập đơn giản, vì RAG là phần được chấm trực tiếp. Nhưng em muốn nghe ý kiến thầy/cô trước khi quyết.

Ngoài ra trong file báo cáo em còn ghi năm câu nữa về multi-turn, về cách đánh giá, và về mức độ phức tạp của màn hình Ban quản lý. Em xin gửi thầy/cô đọc thêm.

Em xin hết ạ. Em cảm ơn thầy/cô.

---

## Ghi chú cho người đọc

- **Nếu bị hỏi vì sao ít commit từ hai bạn kia:** trả lời thẳng — theo kế hoạch hai bạn bắt đầu từ 9/8, và phần front-end bị chặn một phần vì em chưa tạo Supabase project đúng hạn. Đừng vòng vo.
- **Nếu bị hỏi RAG bao giờ xong:** 10/8 có pipeline, 11/8 tích hợp xong. Đừng hứa sớm hơn.
- **Nếu demo lỗi:** có sẵn ảnh chụp màn hình các bước, hoặc đọc thẳng số liệu trong báo cáo. Đừng debug trước mặt mentor.
- **Nếu thiếu thời gian:** bỏ bước chat (bước 6-7 trong demo), giữ bằng được bước so sánh chủ hộ với người thuê và bước đổi hồ sơ.
