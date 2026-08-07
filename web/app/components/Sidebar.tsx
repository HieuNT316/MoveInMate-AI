"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Building2,
  LayoutDashboard,
  Bot,
  ClipboardList,
  UserRound,
  Plus,
} from "lucide-react";

const menus = [
  { title: "Tổng quan", icon: LayoutDashboard, href: "/dashboard" },
  { title: "AI Chat", icon: Bot, href: "/chat" },
  { title: "Checklist & Tiến độ", icon: ClipboardList, href: "/checklist" },
  { title: "Hồ sơ", icon: UserRound, href: "/profile" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-72 shrink-0 bg-ink text-white/90 min-h-screen flex flex-col">
      {/* Logo */}
      <div className="px-7 py-8 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-gold/40 bg-gold/10">
            <Building2 className="h-5 w-5 text-gold-soft" strokeWidth={1.5} />
          </div>
          <div>
            <h1 className="font-display text-lg font-semibold tracking-wide text-white">
              MoveInMate
            </h1>
            <p className="text-[11px] uppercase tracking-[0.2em] text-gold-soft/80">
              AI Concierge
            </p>
          </div>
        </div>
      </div>

      {/* New Chat */}
      <div className="px-6 pt-6">
        <Link
          href="/chat"
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-gold/50 bg-gradient-to-b from-gold to-gold/80 py-3 text-sm font-medium text-ink shadow-[0_8px_20px_-8px_rgba(176,141,79,0.6)] transition hover:shadow-[0_10px_24px_-6px_rgba(176,141,79,0.75)]"
        >
          <Plus className="h-4 w-4" strokeWidth={2} />
          Cuộc trò chuyện mới
        </Link>
      </div>

      {/* Menu */}
      <nav className="flex-1 px-4 pt-8 space-y-1">
        <p className="px-3 pb-2 text-[11px] font-medium uppercase tracking-[0.18em] text-white/35">
          Điều hướng
        </p>
        {menus.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-3.5 rounded-lg px-3.5 py-3 text-sm transition-colors ${
                active
                  ? "bg-white/[0.07] text-white"
                  : "text-white/60 hover:bg-white/[0.04] hover:text-white/90"
              }`}
            >
              <Icon
                className={`h-[18px] w-[18px] ${active ? "text-gold-soft" : "text-white/40 group-hover:text-gold-soft/80"}`}
                strokeWidth={1.75}
              />
              <span className={active ? "font-medium" : ""}>{item.title}</span>
              {active && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-gold-soft" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div className="border-t border-white/10 p-5">
        <Link
          href="/profile"
          className="flex items-center gap-3 rounded-lg px-2 py-2 transition hover:bg-white/[0.05]"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-full border border-gold/40 bg-gold/15 font-display text-base text-gold-soft">
            M
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-white">Minh Thu</p>
            <p className="truncate text-xs text-white/40">Căn hộ A1 · 1208</p>
          </div>
        </Link>
      </div>
    </aside>
  );
}
