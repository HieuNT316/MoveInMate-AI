# Bàn giao backend cho Hiếu

Tài liệu này ghi lại các hạng mục backend phát sinh trong quá trình Minh Thu chỉnh UI. Nhánh của Minh Thu không triển khai các thay đổi dưới `src/`; Hiếu có thể xử lý các hạng mục dưới đây trên nhánh backend riêng.

## 1. Chuẩn hóa phản hồi AI khi không đủ dữ liệu

Hiện mô hình đôi khi tự trả lời theo kiểu “không đủ thông tin trong ngữ cảnh”, nhưng API vẫn có thể gắn nguồn gần đúng. Backend cần nhận diện trường hợp này và trả về nhất quán:

- `answer_source = "no_context"`
- `sources = []`
- Không hiển thị tài liệu tham khảo không thực sự hỗ trợ câu trả lời.

Vị trí gợi ý: `src/agents/nodes/generate.py`.

Kiểm thử cần có: mô phỏng mô hình từ chối vì thiếu ngữ cảnh và xác nhận API không trả nguồn gần nghĩa.

## 2. Giới hạn tần suất gọi `/chat`

Thêm rate limit theo người dùng cho môi trường production:

- Mặc định đề xuất: 20 yêu cầu/phút/người dùng.
- Khi vượt giới hạn trả HTTP `429` với thông báo dễ hiểu.
- Cho phép cấu hình bằng biến môi trường, ví dụ `CHAT_RATE_LIMIT_PER_MINUTE`.
- Nếu chạy nhiều instance, dùng kho chia sẻ như Redis thay cho bộ nhớ của từng process.

Vị trí gợi ý: `src/api/routes.py`, `src/config.py`, một service rate-limit riêng.

Kiểm thử cần có: request trong hạn mức thành công; request vượt hạn mức nhận `429`.

## 3. Che dữ liệu cá nhân trước khi lưu lịch sử chat

Trước khi ghi vào `chat_history`, che tối thiểu:

- Email
- Số điện thoại Việt Nam
- CCCD 12 chữ số

Nội dung gửi vào luồng xử lý AI không nhất thiết phải bị thay đổi; yêu cầu chính là bản lưu lâu dài không chứa dữ liệu nhạy cảm dạng thô.

Vị trí gợi ý: `src/services/store.py` và một service privacy riêng.

Kiểm thử cần có: lưu tin nhắn chứa đủ ba loại dữ liệu trên và xác nhận bản ghi đã được che.

## 4. Hợp đồng với frontend

Frontend của Minh Thu đang giữ nguyên các API hiện có và đã chuẩn bị cách hiển thị cho trạng thái thiếu ngữ cảnh. Khi backend thay đổi, cần giữ tương thích ngược với kiểu dữ liệu hiện tại; không đổi tên endpoint hoặc trường phản hồi nếu chưa thống nhất với frontend.

## Tiêu chí hoàn tất

- Không sửa UI trong `web/` từ nhánh backend.
- Chạy thành công `pytest -q`.
- Chạy thành công kiểm tra lint/format backend của dự án.
- Bổ sung biến môi trường mới vào `.env.example` và cập nhật tài liệu vận hành sau khi code đã được merge.
