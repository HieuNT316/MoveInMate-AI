"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Building2, LayoutDashboard, LogOut } from "lucide-react";

import { api, clearUserId, type Profile } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { signOut } from "../../lib/session";

/**
 * Sidebar riêng cho khu vực BQL (/bql/*). Chỉ có "Tổng quan" vì đây là scope
 * duy nhất đã làm — xem docs/ROLES_AND_PLAN.md mục 10 (Dashboard BQL tối
 * giản, W4). Các trang khác của BQL (duyệt yêu cầu, giấy tờ, nội quy) chưa
 * có API thật nên chưa thêm vào đây.
 */
const menus = [
  { title: "Tổng quan", icon: LayoutDashboard, href: "/bql/dashboard" },
];

export default function BQLSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { userId, ready } = useDemoUser();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [failed, setFailed] = useState(false);

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
    <aside className="w-72 shrink-0 bg-surface text-ink border-r border-border h-screen flex flex-col overflow-y-auto">
      <div className="px-7 py-8 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gold">
            <Building2 className="h-5 w-5 text-white" strokeWidth={1.5} />
          </div>
          <div>
            <h1 className="font-display text-lg font-semibold tracking-wide text-ink">
              MoveInMate
            </h1>
            <p className="text-[11px] uppercase tracking-[0.2em] text-gold">
              Ban Quản Lý
            </p>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-4 pt-8 space-y-1">
        <p className="px-3 pb-2 text-[11px] font-medium uppercase tracking-[0.18em] text-muted">
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
                  ? "bg-gold-tint text-gold"
                  : "text-ink/70 hover:bg-background hover:text-ink"
              }`}
            >
              <Icon
                className={`h-[18px] w-[18px] ${active ? "text-gold" : "text-muted group-hover:text-gold/70"}`}
                strokeWidth={1.75}
              />
              <span className={active ? "font-medium" : ""}>{item.title}</span>
              {active && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-gold" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-5">
        <div className="flex items-center gap-2 rounded-lg px-2 py-2">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gold-tint font-display text-base text-gold">
              {profile ? profile.full_name.charAt(0).toUpperCase() : "?"}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-ink">
                {profile
                  ? profile.full_name
                  : failed
                    ? "Chưa kết nối backend"
                    : "Đang tải..."}
              </p>
              <p className="truncate text-xs text-muted">Ban Quản Lý</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            aria-label="Đăng xuất"
            title="Đăng xuất"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted transition hover:bg-background hover:text-gold"
          >
            <LogOut className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </aside>
  );
}
