"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, ChevronRight, LogOut, UserRound } from "lucide-react";

import { api, clearUserId, type Notification, type Profile } from "../../lib/api";
import { signOut } from "../../lib/session";
import { useDemoUser } from "../../lib/useDemoUser";

const titles: Record<string, { title: string; subtitle: string }> = {
  "/dashboard": { title: "Trang chủ", subtitle: "Đây là tiến độ hành trình nhận nhà của bạn" },
  "/chat": { title: "Trợ lý AI", subtitle: "Hỗ trợ bạn hoàn thành từng thủ tục nhận nhà" },
  "/checklist": {
    title: "Việc cần làm",
    subtitle: "Theo dõi các thủ tục và hoàn thành từng bước nhận nhà",
  },
  "/profile": { title: "Tài khoản", subtitle: "Thông tin cá nhân, căn hộ và bảo mật" },
  "/documents": { title: "Hồ sơ", subtitle: "Quản lý hồ sơ và giấy tờ bạn đã nộp" },
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
  const router = useRouter();
  const current = titles[pathname] ?? { title: "MoveInMate AI", subtitle: "" };
  const { userId, ready } = useDemoUser();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [openPanel, setOpenPanel] = useState<"notifications" | "account" | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ready) return;
    api.getNotifications(userId).then(setNotifications).catch(() => setNotifications([]));
    api.getProfile(userId).then(setProfile).catch(() => setProfile(null));
  }, [pathname, ready, userId]);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!panelRef.current?.contains(event.target as Node)) setOpenPanel(null);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const handleLogout = async () => {
    await signOut().catch(() => undefined);
    clearUserId();
    router.replace("/login");
  };

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

      <div ref={panelRef} className="relative flex items-center gap-5">
        <button
          type="button"
          onClick={() => setOpenPanel((value) => value === "account" ? null : "account")}
          aria-label="Mở menu tài khoản"
          aria-expanded={openPanel === "account"}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-white bg-white/90 text-ink shadow-sm transition hover:border-blue-200 lg:hidden"
        >
          {profile ? (
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-50 text-xs font-bold text-blue-700">
              {profile.full_name.charAt(0).toUpperCase()}
            </span>
          ) : (
            <UserRound className="h-[18px] w-[18px]" strokeWidth={1.75} />
          )}
        </button>
        <button
          type="button"
          onClick={() => setOpenPanel((value) => value === "notifications" ? null : "notifications")}
          aria-label={`${notifications.length} thông báo cần xử lý`}
          aria-expanded={openPanel === "notifications"}
          className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-white bg-white/90 text-ink shadow-sm transition hover:border-blue-200"
        >
          <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} />
          {notifications.length > 0 && (
            <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
              {notifications.length > 9 ? "9+" : notifications.length}
            </span>
          )}
        </button>

        {openPanel === "account" && (
          <div className="absolute right-0 top-12 z-50 w-[min(20rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-border bg-white shadow-xl lg:hidden">
            <div className="border-b border-border bg-gradient-to-br from-white to-blue-50/70 px-4 py-4">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600 font-display text-base font-bold text-white">
                  {profile?.full_name.charAt(0).toUpperCase() ?? "?"}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink">{profile?.full_name ?? "Tài khoản"}</p>
                  <p className="truncate text-xs text-muted">{profile?.role === "admin" ? "Ban Quản lý" : profile?.email ?? "Đang tải thông tin..."}</p>
                </div>
              </div>
            </div>
            {profile?.role !== "admin" && (
              <Link
                href="/profile"
                onClick={() => setOpenPanel(null)}
                className="flex items-center gap-3 px-4 py-3.5 text-sm font-medium text-ink transition hover:bg-blue-50"
              >
                <UserRound className="h-4 w-4 text-blue-600" />
                Thông tin và bảo mật
                <ChevronRight className="ml-auto h-4 w-4 text-muted" />
              </Link>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="flex w-full items-center gap-3 border-t border-border px-4 py-3.5 text-left text-sm font-semibold text-red-600 transition hover:bg-red-50"
            >
              <LogOut className="h-4 w-4" />
              Đăng xuất
            </button>
          </div>
        )}

        {openPanel === "notifications" && (
          <div className="absolute right-0 top-12 z-50 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-border bg-white shadow-xl">
            <div className="border-b border-border px-4 py-3">
              <p className="font-semibold text-ink">Thông báo</p>
              <p className="text-xs text-muted">Các việc đang cần bạn xử lý</p>
            </div>
            {notifications.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-muted">Bạn không có việc nào cần nhắc.</p>
            ) : (
              <div className="max-h-[24rem] divide-y divide-border overflow-y-auto">
                {notifications.map((notification) => (
                  <Link
                    key={notification.id}
                    href={notification.href}
                    onClick={() => setOpenPanel(null)}
                    className="block px-4 py-3.5 transition hover:bg-blue-50"
                  >
                    <div className="flex gap-3">
                      <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${notification.kind === "rejected" ? "bg-red-500" : notification.kind === "needs_info" ? "bg-amber-500" : "bg-blue-500"}`} />
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-ink">{notification.title}</p>
                        <p className="mt-0.5 line-clamp-2 text-xs text-muted">{notification.message}</p>
                        <p className="mt-2 text-xs font-semibold text-gold">{notification.action_label} →</p>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
