"use client";

import { usePathname } from "next/navigation";
import { Bell } from "lucide-react";

const titles: Record<string, { title: string; subtitle: string }> = {
  "/dashboard": { title: "Tổng quan", subtitle: "Chào mừng bạn quay trở lại" },
  "/chat": { title: "AI Chat", subtitle: "Hỏi đáp thủ tục nhận nhà" },
  "/checklist": {
    title: "Checklist & Tiến độ",
    subtitle: "Tick việc đã làm, nộp hồ sơ và theo dõi phản hồi của Ban quản lý",
  },
  "/profile": { title: "Hồ sơ", subtitle: "Thông tin cư dân" },
  "/onboarding": {
    title: "Thiết lập hồ sơ",
    subtitle: "Cho chúng tôi biết về căn hộ của bạn",
  },
  "/bql/dashboard": {
    title: "Tổng quan",
    subtitle: "Theo dõi tiến độ onboarding toàn khu",
  },
  "/bql/residents": {
    title: "Quản lý cư dân",
    subtitle: "Tạo tài khoản, theo dõi tiến độ và xem đơn đã nộp của từng cư dân",
  },
  "/bql/applications": {
    title: "Quản lý đơn",
    subtitle: "Hồ sơ trực tuyến cư dân đã nộp — duyệt và cập nhật trạng thái",
  },
};

export default function Header() {
  const pathname = usePathname();
  const current = titles[pathname] ?? { title: "MoveInMate AI", subtitle: "" };

  return (
    <header className="sticky top-0 z-10 flex h-20 items-center justify-between border-b border-border bg-surface/90 px-8 backdrop-blur">
      <div>
        <h2 className="font-display text-2xl font-semibold text-ink">
          {current.title}
        </h2>
        {current.subtitle && (
          <p className="text-sm text-muted">{current.subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-5">
        {/* Chưa có hệ thống thông báo ở backend (xem BQLSidebar — mục "Thông
            báo" đang khoá "Sắp có") — khoá luôn nút này, không hiện chấm đỏ
            giả vờ có tin mới. */}
        <button
          disabled
          aria-label="Thông báo — chưa có hệ thống thông báo"
          title="Sắp có — chưa có hệ thống thông báo ở backend"
          className="flex h-10 w-10 cursor-not-allowed items-center justify-center rounded-full border border-border text-ink/40"
        >
          <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} />
        </button>
      </div>
    </header>
  );
}
