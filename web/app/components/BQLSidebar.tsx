"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, LogOut } from "lucide-react";

import { api, clearUserId, type Profile } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { signOut } from "../../lib/session";
import { BQL_NAV } from "../../lib/nav";
import LogoMark from "./LogoMark";

export default function BQLSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { userId, ready } = useDemoUser();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [failed, setFailed] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => { setCollapsed(window.localStorage.getItem("moveinmate.sidebar-collapsed") === "1"); }, []);
  const toggleCollapsed = () => setCollapsed((current) => { window.localStorage.setItem("moveinmate.sidebar-collapsed", current ? "0" : "1"); return !current; });

  useEffect(() => {
    if (!ready) return;
    api
      .getProfile(userId)
      .then(setProfile)
      .catch(() => setFailed(true));
  }, [ready, userId]);

  const handleLogout = async () => {
    await signOut().catch(() => {});
    clearUserId();
    router.push("/login");
  };

  return (
    <aside className={`relative hidden h-screen shrink-0 flex-col overflow-y-auto border-r border-white/80 bg-white/88 text-[#1E293B] shadow-[8px_0_32px_-28px_rgba(0,45,98,0.55)] backdrop-blur-xl transition-[width] duration-300 lg:flex ${collapsed ? "w-20" : "w-72"}`}>
      <div className={`border-b border-[#B6C4D6]/70 bg-gradient-to-br from-white to-blue-50/60 py-8 ${collapsed ? "px-3" : "px-7"}`}>
        <div className={`flex items-center ${collapsed ? "justify-center" : "gap-3"}`}>
          <LogoMark size={collapsed ? 44 : 52} />
          {!collapsed && <div>
            <h1 className="font-display text-lg font-semibold tracking-wide text-[#1E293B]">
              MoveInMate
            </h1>
            <p className="text-[11px] uppercase tracking-[0.2em] text-[#2563EB]">
              Ban Quản Lý
            </p>
          </div>}
        </div>
      </div>
      <button type="button" onClick={toggleCollapsed} title={collapsed ? "Mở rộng sidebar" : "Thu gọn sidebar"} aria-label={collapsed ? "Mở rộng sidebar" : "Thu gọn sidebar"} className="absolute right-2 top-[92px] z-10 flex h-7 w-7 items-center justify-center rounded-lg border border-[#B6C4D6] bg-white text-[#64748B] shadow-sm hover:text-[#2563EB]">{collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}</button>

      <nav className={`flex-1 space-y-1 pt-8 ${collapsed ? "px-2" : "px-4"}`}>
        <p className={`px-3 pb-2 text-[11px] font-medium uppercase tracking-[0.18em] text-[#64748B] ${collapsed ? "sr-only" : ""}`}>
          Điều hướng
        </p>
        {BQL_NAV.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.title : undefined}
              className={`group flex items-center gap-3.5 rounded-xl px-3.5 py-3 text-sm transition-all ${
                active
                  ? "bg-gradient-to-r from-[#EFF6FF] to-cyan-50/50 text-[#2563EB] shadow-sm ring-1 ring-[#2563EB]/10"
                  : "text-[#334155] hover:translate-x-0.5 hover:bg-[#F8FAFC] hover:text-[#1E293B]"
              }`}
            >
              <Icon
                className={`h-[18px] w-[18px] ${active ? "text-[#2563EB]" : "text-[#64748B] group-hover:text-[#334155]"}`}
                strokeWidth={1.75}
              />
              {!collapsed && <span className={active ? "font-medium" : ""}>{item.title}</span>}
              {active && !collapsed && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[#2563EB]" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className={`border-t border-[#B6C4D6] ${collapsed ? "p-2" : "p-5"}`}>
        <div className={`flex items-center rounded-lg py-2 ${collapsed ? "flex-col gap-1 px-0" : "gap-2 px-2"}`}>
          <div className={`flex min-w-0 items-center ${collapsed ? "justify-center" : "flex-1 gap-3"}`}>
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#EFF6FF] font-display text-base text-[#2563EB]">
              {profile ? profile.full_name.charAt(0).toUpperCase() : "?"}
            </div>
            {!collapsed && <div className="min-w-0">
              <p className="truncate text-sm font-medium text-[#1E293B]">
                {profile
                  ? profile.full_name
                  : failed
                    ? "Chưa kết nối backend"
                    : "Đang tải..."}
              </p>
              <p className="truncate text-xs text-[#64748B]">Ban Quản Lý</p>
            </div>}
          </div>
          <button
            onClick={handleLogout}
            aria-label="Đăng xuất"
            title="Đăng xuất"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[#64748B] transition hover:bg-[#F8FAFC] hover:text-[#2563EB]"
          >
            <LogOut className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </aside>
  );
}
