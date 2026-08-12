/**
 * Dữ liệu giả cho trang "Thông báo & Nội quy".
 *
 * Không nằm trong User Story nào ở docs/PROJECT_CHARTER.md mục 5 (US-01…09) —
 * đây là nội dung tham khảo lấy cảm hứng từ frontend/ do bạn cung cấp, KHÔNG
 * có API thật (không có bảng ANNOUNCEMENTS/REGULATIONS trong schema mục 6).
 * Giữ lại vì vô hại (chỉ đọc, không ảnh hưởng luồng onboarding/checklist),
 * nhưng cần team xác nhận có đưa vào scope trước khi coi là chính thức.
 */

export type Announcement = {
  id: string;
  title: string;
  body: string;
  category: "general" | "maintenance" | "event" | "security";
  pinned: boolean;
  author: string;
  date: string;
};

export type RegulationSection = { heading: string; content: string };

export type Regulation = {
  id: string;
  title: string;
  summary: string;
  version: string;
  effectiveDate: string;
  sections: RegulationSection[];
};

export const CATEGORY_LABEL: Record<Announcement["category"], string> = {
  general: "Chung",
  maintenance: "Bảo trì",
  event: "Sự kiện",
  security: "An ninh",
};

export const mockAnnouncements: Announcement[] = [
  {
    id: "ANN-001",
    title: "Lịch cắt nước bảo trì hệ thống bơm tháp A2 - A3",
    body: "Tạm ngưng cấp nước để bảo trì hệ thống bơm tổng: 09:00–13:00, ngày 04/08/2026, toàn bộ tháp A2 và A3. Kính mong cư dân chủ động trữ nước sinh hoạt.",
    category: "maintenance",
    pinned: true,
    author: "Trần Thị Lan",
    date: "2026-08-04",
  },
  {
    id: "ANN-002",
    title: "Khai trương khu vui chơi trẻ em tầng 2 khối đế",
    body: "Khu vui chơi trẻ em tại tầng 2 khối đế chính thức mở cửa từ 10/08/2026, hoạt động 08:00–20:00 hàng ngày.",
    category: "event",
    pinned: true,
    author: "Trần Thị Lan",
    date: "2026-08-03",
  },
  {
    id: "ANN-003",
    title: "Nhắc nhở đăng ký thẻ xe trước ngày nhận nhà",
    body: "Khuyến nghị hoàn tất đăng ký thẻ xe trước ngày nhận nhà. Hồ sơ cần: CCCD, đăng ký xe, đăng kiểm còn hiệu lực.",
    category: "general",
    pinned: false,
    author: "Lê Thị Hoa",
    date: "2026-08-02",
  },
  {
    id: "ANN-004",
    title: "Cập nhật quy trình xác nhận cư trú",
    body: "Từ 01/08/2026, BQL rút ngắn thời gian xét duyệt giấy xác nhận cư trú xuống còn 1–2 ngày làm việc.",
    category: "general",
    pinned: false,
    author: "Trần Thị Lan",
    date: "2026-08-01",
  },
  {
    id: "ANN-005",
    title: "Tăng cường an ninh khu vực hầm B1 - B3",
    body: "Bổ sung camera an ninh và tăng ca trực bảo vệ tại khu vực hầm gửi xe B1-B3, áp dụng từ 30/07/2026.",
    category: "security",
    pinned: false,
    author: "Phạm Văn Đức",
    date: "2026-07-30",
  },
];

export const mockRegulations: Regulation[] = [
  {
    id: "REG-001",
    title: "Nội quy Sinh hoạt Chung cư",
    summary: "Quy định chung về nếp sống văn minh, giờ giấc sinh hoạt và sử dụng không gian chung.",
    version: "v2.1",
    effectiveDate: "2026-02-01",
    sections: [
      { heading: "Giờ giấc sinh hoạt", content: "Hạn chế gây tiếng ồn lớn trong khung giờ 22:00–07:00 hàng ngày." },
      { heading: "Sử dụng không gian chung", content: "Không để đồ đạc cá nhân, giày dép ngoài hành lang; không hút thuốc tại khu vực chung." },
      { heading: "Rác thải", content: "Phân loại rác và bỏ đúng nơi quy định, không để rác trước cửa căn hộ quá 24 giờ." },
    ],
  },
  {
    id: "REG-002",
    title: "Nội quy Quản lý & Sử dụng Bãi đỗ xe",
    summary: "Quy định về đăng ký, ra vào và đỗ xe tại các tầng hầm B1-B3.",
    version: "v2.1",
    effectiveDate: "2026-02-05",
    sections: [
      { heading: "Đăng ký thẻ xe", content: "Mọi phương tiện ra vào hầm bắt buộc đăng ký thẻ xe, xuất trình đăng ký xe và đăng kiểm còn hiệu lực." },
      { heading: "Vị trí đỗ xe", content: "Đỗ đúng vị trí đã đăng ký, không đỗ tại lối đi hoặc lối thoát hiểm." },
    ],
  },
  {
    id: "REG-003",
    title: "Quy trình Kích hoạt Tiện ích Điện, Nước",
    summary: "Hướng dẫn quy trình kích hoạt điện, nước cho cư dân mới nhận nhà.",
    version: "v1.3",
    effectiveDate: "2026-01-25",
    sections: [
      { heading: "Kiểm tra kỹ thuật ban đầu", content: "Kiểm tra CB tổng tại hộp điện, chụp ảnh chỉ số đồng hồ điện nước ban đầu." },
      { heading: "Xác nhận và ký hợp đồng", content: "Kỹ thuật viên BQL xác nhận chỉ số trong 24h, sau đó ký hợp đồng cung cấp dịch vụ online." },
    ],
  },
  {
    id: "REG-004",
    title: "Nội quy Nuôi Thú cưng",
    summary: "Quy định về đăng ký và quản lý thú cưng trong khu dân cư.",
    version: "v1.0",
    effectiveDate: "2026-03-10",
    sections: [
      { heading: "Đăng ký thú cưng", content: "Chủ hộ nuôi chó, mèo phải đăng ký với BQL và tiêm phòng đầy đủ." },
      { heading: "Khi di chuyển tại khu vực chung", content: "Thú cưng phải được rọ mõm hoặc bế/địu khi ở hành lang, thang máy, sảnh chung." },
    ],
  },
];
