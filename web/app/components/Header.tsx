"use client";

import { usePathname } from "next/navigation";
import { Bell } from "lucide-react";

const titles: Record<string, { title: string; subtitle: string }> = {
  "/dashboard": { title: "Trang chủ", subtitle: "Đây là tiến độ hành trình nhận nhà của bạn" },
  "/chat": { title: "Trợ lý AI", subtitle: "Hỗ trợ bạn hoàn thành từng thủ tục nhận nhà" },
  "/checklist": {
    title: "Việc cần làm",
    subtitle: "Theo dõi các thủ tục và hoàn thành từng bước nhận nhà",
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
    <header className="glass-header sticky top-0 z-10 flex h-16 items-center justify-between border-b border-white/70 px-4 backdrop-blur-xl lg:h-20 lg:px-8">
      <div className="min-w-0">
        <div className="flex items-center gap-3">
          <span className="hidden h-9 w-1 rounded-full bg-gradient-to-b from-[#2563EB] to-[#22C1DC] lg:block" />
          <div className="min-w-0">
        <h2 className="truncate font-display text-lg font-bold tracking-[-0.02em] text-ink lg:text-2xl">
          {current.title}
        </h2>
        {current.subtitle && (
          <p className="hidden text-sm text-muted lg:block">{current.subtitle}</p>
        )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-5">
        {/* Chưa có hệ thống thông báo ở backend (xem BQLSidebar — mục "Thông
            báo" đang khoá "Sắp có") — khoá luôn nút này, không hiện chấm đỏ
            giả vờ có tin mới. */}
        <button
          disabled
          aria-label="Thông báo — chưa có hệ thống thông báo"
          title="Sắp có — chưa có hệ thống thông báo ở backend"
          className="flex h-10 w-10 cursor-not-allowed items-center justify-center rounded-xl border border-white bg-white/70 text-ink/35 shadow-sm"
        >
          <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} />
        </button>
      </div>
    </header>
  );
}
