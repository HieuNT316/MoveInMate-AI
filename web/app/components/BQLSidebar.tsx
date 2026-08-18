"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Building2, LogOut } from "lucide-react";

import { api, clearUserId, type Profile } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { signOut } from "../../lib/session";
import { BQL_NAV } from "../../lib/nav";

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
    <aside className="flex h-screen w-72 shrink-0 flex-col overflow-y-auto border-r border-[#E2E8F0] bg-white text-[#1E293B]">
      <div className="border-b border-[#E2E8F0] px-7 py-8">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-[#2563EB]">
            <Building2 className="h-5 w-5 text-white" strokeWidth={1.5} />
          </div>
          <div>
            <h1 className="font-display text-lg font-semibold tracking-wide text-[#1E293B]">
              MoveInMate
            </h1>
            <p className="text-[11px] uppercase tracking-[0.2em] text-[#2563EB]">
              Ban Quản Lý
            </p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-4 pt-8">
        <p className="px-3 pb-2 text-[11px] font-medium uppercase tracking-[0.18em] text-[#94A3B8]">
          Điều hướng
        </p>
        {BQL_NAV.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-3.5 rounded-lg px-3.5 py-3 text-sm transition-colors ${
                active
                  ? "bg-[#EFF6FF] text-[#2563EB]"
                  : "text-[#475569] hover:bg-[#F8FAFC] hover:text-[#1E293B]"
              }`}
            >
              <Icon
                className={`h-[18px] w-[18px] ${active ? "text-[#2563EB]" : "text-[#94A3B8] group-hover:text-[#475569]"}`}
                strokeWidth={1.75}
              />
              <span className={active ? "font-medium" : ""}>{item.title}</span>
              {active && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[#2563EB]" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[#E2E8F0] p-5">
        <div className="flex items-center gap-2 rounded-lg px-2 py-2">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#EFF6FF] font-display text-base text-[#2563EB]">
              {profile ? profile.full_name.charAt(0).toUpperCase() : "?"}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-[#1E293B]">
                {profile
                  ? profile.full_name
                  : failed
                    ? "Chưa kết nối backend"
                    : "Đang tải..."}
              </p>
              <p className="truncate text-xs text-[#94A3B8]">Ban Quản Lý</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            aria-label="Đăng xuất"
            title="Đăng xuất"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[#94A3B8] transition hover:bg-[#F8FAFC] hover:text-[#2563EB]"
          >
            <LogOut className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </aside>
  );
}
