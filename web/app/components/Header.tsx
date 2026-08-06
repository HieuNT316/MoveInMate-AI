"use client";

import { usePathname } from "next/navigation";
import { Bell, Search } from "lucide-react";

const titles: Record<string, { title: string; subtitle: string }> = {
  "/dashboard": { title: "Tổng quan", subtitle: "Chào mừng bạn quay trở lại" },
  "/chat": { title: "AI Chat", subtitle: "Hỏi đáp thủ tục nhận nhà" },
  "/checklist": { title: "Checklist & Tiến độ", subtitle: "Theo dõi hành trình bàn giao của bạn" },
  "/profile": { title: "Hồ sơ", subtitle: "Thông tin cư dân" },
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
        <div className="hidden items-center gap-2 rounded-full border border-border bg-background px-4 py-2 text-sm text-muted md:flex">
          <Search className="h-4 w-4" strokeWidth={1.75} />
          <span>Tìm kiếm...</span>
        </div>

        <button
          aria-label="Thông báo"
          className="relative flex h-10 w-10 items-center justify-center rounded-full border border-border text-ink/70 transition hover:border-gold/50 hover:text-gold"
        >
          <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-gold" />
        </button>

        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-ink font-display text-sm text-gold-soft ring-1 ring-gold/30">
          M
        </div>
      </div>
    </header>
  );
}
