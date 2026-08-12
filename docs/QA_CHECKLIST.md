# QA Checklist — kiểm tra thủ công end-to-end

> Dùng file này để tự test trên trình duyệt trước khi demo (GATE 2 và các mốc
> sau). Không cần cài thêm gì — chỉ cần backend + frontend chạy local.
> Đánh dấu ✅/❌ vào cột Kết quả khi chạy thật.

## 0. Chuẩn bị

- [ ] Backend chạy: từ gốc repo, `uvicorn src.main:app --reload`. Log không
      báo lỗi thiếu biến môi trường.
- [ ] Kiểm tra `.env` (gốc repo) có `GOOGLE_API_KEY` là key thật, không phải
      placeholder `your-google-ai-studio-key-here` — thiếu key này thì mọi
      câu hỏi AI Chat sẽ báo lỗi 503 dù các trang khác vẫn chạy bình thường.
- [ ] Frontend chạy: `cd web && npm run dev` → mở `http://localhost:3000`.
- [ ] Test nhanh backend sống chưa (không cần trình duyệt):
      `curl http://localhost:8000/api/v1/auth/demo-accounts` → phải trả JSON,
      không phải rỗng/lỗi kết nối.
- [ ] **Vừa merge/pull code mới?** Xoá cache rồi khởi động lại cả 2 server:
      `rm -rf web/.next` — dev server cũ có thể giữ bản biên dịch lỗi từ lúc
      file còn dấu conflict, dù file trên đĩa đã sạch.

| Bước | Kết quả |
|---|---|

## 1. Cư dân — luồng chính (US-01, 02, 04, 05, 06)

Đăng nhập bằng một tài khoản demo **cư dân** (bấm chọn trong danh sách ở
`/login`, không gõ tay).

| # | Bước | Kỳ vọng | Kết quả |
|---|------|---------|---------|
| 1.1 | Đăng nhập tài khoản cư dân **chưa** onboarding | Chuyển tới `/onboarding` | |
| 1.2 | Điền form onboarding (chủ hộ/thuê, loại căn, có xe, tiện ích) → Hoàn tất | Chuyển tới `/checklist` hoặc `/dashboard`, không lỗi | |
| 1.3 | Đăng nhập tài khoản cư dân **đã** onboarding | Chuyển thẳng tới `/dashboard`, không quay lại onboarding | |
| 1.4 | Vào `/checklist` | Danh sách thủ tục đúng theo hồ sơ (có xe → có mục thẻ xe; không xe → không có) | |
| 1.5 | Tick hoàn thành 1 mục | Mục chuyển trạng thái, thanh tiến độ tổng cập nhật ngay | |
| 1.6 | Vào `/chat`, hỏi "Làm thẻ xe cần giấy tờ gì?" | Có câu trả lời + nguồn trích dẫn (không phải câu từ chối) | |
| 1.7 | Hỏi câu ngoài phạm vi (vd "giá vàng hôm nay") | Trả lời từ chối lịch sự, không bịa | |
| 1.8 | Hỏi câu kiểu "nộp hồ sơ thẻ xe ở đâu" | Nếu có nút "Đến mục này" → bấm vào, phải nhảy đúng tới mục đó trong `/checklist` và cuộn tới, tô sáng | |
| 1.9 | Vào `/profile`, sửa 1 trường (vd thêm tiện ích) → Lưu | Lưu thành công; quay lại `/checklist` thấy mục mới xuất hiện | |

## 2. Ban quản lý (US-00, US-12-mini)

Đăng nhập bằng tài khoản demo **BQL/admin**.

| # | Bước | Kỳ vọng | Kết quả |
|---|------|---------|---------|
| 2.1 | Đăng nhập tài khoản admin | Chuyển thẳng tới `/bql/dashboard` | |
| 2.2 | Xem số liệu tổng quan | Tổng cư dân, % tiến độ trung bình, số chưa thiết lập hồ sơ hiển thị đúng | |
| 2.3 | Mục "Cư dân cần hỗ trợ" | Chỉ liệt kê cư dân đã onboarding nhưng tiến độ thấp | |
| 2.4 | Bấm "Tạo tài khoản cư dân" → điền đủ form → Tạo | Hiện mật khẩu tạm đúng một lần, có nút chép | |
| 2.5 | Bấm "Xong" sau khi tạo | Dashboard tự load lại, cư dân mới xuất hiện trong bảng | |
| 2.6 | Đăng nhập lại bằng account thường (không phải admin) rồi cố vào `/bql/dashboard` bằng URL trực tiếp | Bị đẩy về `/dashboard`, không xem được trang BQL | |

## 3. PWA (T13)

| # | Bước | Kỳ vọng | Kết quả |
|---|------|---------|---------|
| 3.1 | Mở `http://localhost:3000/manifest.webmanifest` | Trả JSON có `name`, `icons` | |
| 3.2 | Mở `http://localhost:3000/pwa/icon-512` | Hiện ảnh icon (nền xanh, chữ "M") | |
| 3.3 | Trên điện thoại/Chrome desktop: menu trình duyệt → "Cài đặt ứng dụng" / "Add to Home Screen" | Cài được, icon đúng hiện trên màn hình chính | |

## 4. Trường hợp lỗi (kiểm tra thông báo có rõ ràng không)

| # | Bước | Kỳ vọng | Kết quả |
|---|------|---------|---------|
| 4.1 | Tắt backend, thử tải `/dashboard` | Hiện thông báo lỗi kết nối rõ ràng, không đứng loading vô hạn | |
| 4.2 | Bật lại backend, reload | Trang tải lại bình thường | |

## Ghi chú khi debug

- **Đứng "Đang tải..." mãi ở `/bql/*`**: thường do `GET /profile` trả 401/403
  — phiên đăng nhập cũ không khớp dữ liệu hiện tại. Đăng xuất, đăng nhập lại
  bằng tài khoản demo trong danh sách.
- **Chat báo lỗi 503**: `GOOGLE_API_KEY` trong `.env` sai/thiếu — xem mục 0.
- **Trang trắng/lỗi parse sau khi merge git**: dev server cũ cache code lúc
  còn dấu `<<<<<<<`/`>>>>>>>`. Dừng server, xoá `web/.next`, chạy lại.
