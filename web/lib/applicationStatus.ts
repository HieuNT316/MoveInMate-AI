import type { Application } from "./api";

/**
 * US-13 — nhãn hiển thị theo `status`, KHÔNG dùng chung một bảng cho cả hai
 * `kind`: `self_declared` (thủ tục làm ở cơ quan khác, BQL chỉ ghi nhận ảnh
 * minh chứng cư dân tự nộp) không được nói "Ban quản lý đang xử lý" — mạo
 * nhận quy trình của cơ quan khác (xem docs/CONTRACT_US13.md mục 2).
 */
export function applicationStatusLabel(app: Application): string {
  if (app.kind === "self_declared") {
    switch (app.status) {
      case "received":
        // Hồ sơ `self_declared` được tạo TRƯỚC khi tải ảnh (2 bước ở
        // SubmitApplicationDialog) — nhãn này từng ghi "đã gửi minh chứng"
        // ngay cả khi `attachments` rỗng, tự mâu thuẫn với ô "Đã tải 0/N
        // giấy tờ" hiện ngay bên dưới. Chỉ áp dụng cho "received": sang
        // "processing" nghĩa là BQL đã động vào hồ sơ (có thể nhận trực
        // tiếp ngoài app), lúc đó không tự suy đoán minh chứng có hay
        // không nữa — cứ hiển thị "Đang xử lý" trung lập như cũ.
        return app.attachments.length > 0
          ? "Đã gửi minh chứng, chờ Ban quản lý ghi nhận"
          : "Đã tạo hồ sơ — cần tải minh chứng để hoàn tất";
      case "processing":
        return "Đang xử lý";
      case "needs_info":
        return "Cần bổ sung minh chứng";
      case "approved":
      case "delivered":
        return "Đã ghi nhận";
      case "rejected":
        return "Bị từ chối";
    }
  }
  switch (app.status) {
    case "received":
      return "Đã tiếp nhận";
    case "processing":
      return "Đang xử lý";
    case "needs_info":
      return "Cần bổ sung";
    case "approved":
      return "Đã duyệt";
    case "delivered":
      return "Đã trả kết quả";
    case "rejected":
      return "Từ chối";
  }
}

// `needs_info`/`rejected` cần cư dân hành động tiếp — làm nổi bật hơn hẳn các
// trạng thái còn lại (xem docs/CONTRACT_US13.md mục 6).
export function applicationStatusTone(status: Application["status"]): string {
  if (status === "rejected") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  if (status === "needs_info") {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (status === "approved" || status === "delivered") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (status === "processing") {
    return "border-blue-200 bg-blue-50 text-blue-700";
  }
  return "border-sky-200 bg-sky-50 text-sky-700";
}
