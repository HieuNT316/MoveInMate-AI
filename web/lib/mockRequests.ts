/**
 * Dữ liệu giả cho trang "Yêu cầu" (US-11 — agent tạo/định tuyến ticket).
 *
 * ⚠️ PHASE 2 theo docs/PROJECT_CHARTER.md mục 4 — chưa có bảng DB hay API
 * thật cho tính năng này (không có trong schema mục 6, không có trong
 * web/lib/api.ts). Trang dùng file này chỉ để dựng UI tham khảo theo yêu
 * cầu thiết kế, KHÔNG gọi backend. Khi team chốt contract US-11 với Hiếu,
 * thay import này bằng lệnh gọi `api.*` thật.
 */

export type RequestStatus =
  | "submitted"
  | "in_review"
  | "approved"
  | "completed";

export type MockRequest = {
  id: string;
  title: string;
  department: string;
  status: RequestStatus;
  code: string;
  updatedAt: string;
  needsBqlReview: boolean;
};

export const REQUEST_STATUS_LABEL: Record<RequestStatus, string> = {
  submitted: "Đã gửi",
  in_review: "Đang xét duyệt",
  approved: "Đã duyệt",
  completed: "Hoàn tất",
};

export const mockRequests: MockRequest[] = [
  {
    id: "req-1",
    title: "Đăng ký thẻ xe ô tô",
    department: "Bộ phận Xe cộ",
    status: "in_review",
    code: "REQ-2026-0802",
    updatedAt: "2026-08-05",
    needsBqlReview: true,
  },
  {
    id: "req-2",
    title: "Kích hoạt điện căn hộ",
    department: "Kỹ thuật",
    status: "approved",
    code: "REQ-2026-0803",
    updatedAt: "2026-08-04",
    needsBqlReview: false,
  },
  {
    id: "req-3",
    title: "Đăng ký thẻ cư dân",
    department: "Ban Quản Lý",
    status: "completed",
    code: "REQ-2026-0798",
    updatedAt: "2026-08-01",
    needsBqlReview: false,
  },
  {
    id: "req-4",
    title: "Tư vấn lắp đặt internet",
    department: "Tiện ích số",
    status: "submitted",
    code: "REQ-2026-0810",
    updatedAt: "2026-08-05",
    needsBqlReview: false,
  },
];
