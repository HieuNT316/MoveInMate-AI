"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Building2, LogOut, Plus } from "lucide-react";

import { api, clearUserId, type Profile } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { signOut } from "../../lib/session";
import { RESIDENT_NAV } from "../../lib/nav";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { userId, ready } = useDemoUser();
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    if (!ready) return;
    api.getProfile(userId).then(setProfile).catch(() => setProfile(null));
  }, [ready, userId]);

  const handleLogout = async () => {
    // Xoá cả hai: session Supabase thật lẫn id demo lưu localStorage — thiếu
    // một trong hai thì đăng nhập lại vẫn dính danh tính cũ.
    await signOut().catch(() => {});
    clearUserId();
    router.push("/login");
  };

  return (
    <aside className="hidden lg:flex w-72 shrink-0 bg-surface text-ink h-screen flex-col overflow-y-auto border-r border-border">
      {/* Logo */}
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
              AI Concierge
            </p>
          </div>
        </div>
      </div>

      {/* New Chat */}
      <div className="px-6 pt-6">
        <Link
          href="/chat"
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-gold py-3 text-sm font-medium text-white shadow-[0_8px_20px_-8px_rgba(0,86,210,0.5)] transition hover:bg-gold-soft"
        >
          <Plus className="h-4 w-4" strokeWidth={2} />
          Cuộc trò chuyện mới
        </Link>
      </div>

      {/* Menu */}
      <nav className="flex-1 px-4 pt-8 space-y-1">
        <p className="px-3 pb-2 text-[11px] font-medium uppercase tracking-[0.18em] text-muted">
          Điều hướng
        </p>
        {RESIDENT_NAV.map((item) => {
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

      {/* User */}
      <div className="border-t border-border p-5">
        <div className="flex items-center gap-2 rounded-lg px-2 py-2 transition hover:bg-background">
          <Link href="/profile" className="flex min-w-0 flex-1 items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gold-tint font-display text-base text-gold">
              {profile ? profile.full_name.charAt(0).toUpperCase() : "?"}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-ink">
                {profile ? profile.full_name : "Đang tải..."}
              </p>
              <p className="truncate text-xs text-muted">
                {profile ? `${profile.building} · ${profile.apartment}` : "—"}
              </p>
            </div>
          </Link>
          <button
            onClick={handleLogout}
            aria-label="Đăng xuất"
            title="Đăng xuất"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted transition hover:bg-surface hover:text-gold"
          >
            <LogOut className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </aside>
  );
}
