/**
 * Dữ liệu giả cho trang "Hồ sơ giấy tờ" (US-10 — duyệt hồ sơ/giấy tờ, bảng
 * APPLICATIONS).
 *
 * ⚠️ PHASE 2 theo docs/PROJECT_CHARTER.md mục 4 và mục 6 ("APPLICATIONS —
 * giữ nguyên thiết kế gốc, chưa migrate ở GATE 2"). Không có API thật —
 * chỉ dựng UI, thay bằng `api.*` khi có contract.
 */

export type DocumentStatus =
  | "not_submitted"
  | "pending_review"
  | "approved"
  | "rejected";

export type MockDocument = {
  id: string;
  group: "identity" | "residency" | "contract" | "vehicle" | "other";
  name: string;
  required: boolean;
  status: DocumentStatus;
  note?: string;
  rejectReason?: string;
  files: { name: string; sizeKb: number }[];
};

export const DOCUMENT_STATUS_LABEL: Record<DocumentStatus, string> = {
  not_submitted: "Chưa nộp",
  pending_review: "Đang xét duyệt",
  approved: "Đã duyệt",
  rejected: "Bị từ chối",
};

export const mockDocuments: MockDocument[] = [
  {
    id: "doc-cccd",
    group: "identity",
    name: "CCCD / CMND",
    required: true,
    status: "approved",
    note: "Chụp rõ cả mặt trước và mặt sau.",
    files: [
      { name: "cccd-mat-truoc.jpg", sizeKb: 793 },
      { name: "cccd-mat-sau.jpg", sizeKb: 779 },
    ],
  },
  {
    id: "doc-hokhau",
    group: "residency",
    name: "Sổ hộ khẩu / Xác nhận cư trú",
    required: false,
    status: "not_submitted",
    note: "Sổ hộ khẩu hoặc giấy xác nhận nơi thường trú hiện tại.",
    files: [],
  },
  {
    id: "doc-hopdong",
    group: "contract",
    name: "Hợp đồng mua bán căn hộ",
    required: true,
    status: "approved",
    note: "Hợp đồng mua bán căn hộ đã ký với chủ đầu tư.",
    files: [{ name: "hop-dong-mua-ban.pdf", sizeKb: 1240 }],
  },
  {
    id: "doc-dangkyxe",
    group: "vehicle",
    name: "Đăng ký xe",
    required: true,
    status: "pending_review",
    files: [{ name: "dang-ky-xe.jpg", sizeKb: 639 }],
  },
  {
    id: "doc-dangkiemxe",
    group: "vehicle",
    name: "Đăng kiểm xe",
    required: true,
    status: "rejected",
    note: "Bắt buộc để hoàn tất đăng ký thẻ xe ô tô.",
    rejectReason:
      "Ảnh mờ, không đọc được ngày hết hạn đăng kiểm. Vui lòng chụp lại rõ nét hơn.",
    files: [{ name: "dang-kiem-xe-cu.jpg", sizeKb: 500 }],
  },
  {
    id: "doc-khac",
    group: "other",
    name: "Giấy tờ khác",
    required: false,
    status: "not_submitted",
    note: "Các giấy tờ bổ sung khác theo yêu cầu của BQL.",
    files: [],
  },
];
