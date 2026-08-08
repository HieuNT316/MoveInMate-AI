"use client";

import { usePathname } from "next/navigation";
import { Bell } from "lucide-react";

import DemoUserSwitcher from "./DemoUserSwitcher";

const titles: Record<string, { title: string; subtitle: string }> = {
  "/dashboard": { title: "Tổng quan", subtitle: "Chào mừng bạn quay trở lại" },
  "/chat": { title: "AI Chat", subtitle: "Hỏi đáp thủ tục nhận nhà" },
  "/checklist": {
    title: "Checklist & Tiến độ",
    subtitle: "Theo dõi hành trình bàn giao của bạn",
  },
  "/profile": { title: "Hồ sơ", subtitle: "Thông tin cư dân" },
  "/onboarding": {
    title: "Thiết lập hồ sơ",
    subtitle: "Cho chúng tôi biết về căn hộ của bạn",
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
        <DemoUserSwitcher />

        <button
          aria-label="Thông báo"
          className="relative flex h-10 w-10 items-center justify-center rounded-full border border-border text-ink/70 transition hover:border-gold/50 hover:text-gold"
        >
          <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-gold" />
        </button>
      </div>
    </header>
  );
}
