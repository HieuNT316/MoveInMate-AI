"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { NavItem } from "../../lib/nav";

/**
 * Điều hướng cho màn hình nhỏ. Ẩn từ `lg` trở lên, nơi sidebar tiếp quản.
 *
 * Chọn thanh tab thay vì drawer + hamburger vì cả hai khu chỉ có 4 mục: bốn
 * mục vừa khít một thanh, nên không cần lớp phủ và không cần trạng thái
 * đóng/mở. Với PWA khai `display: standalone`, đây cũng là thứ khiến sản phẩm
 * đọc ra như một app thay vì một trang web bị bóp lại.
 */
export default function MobileTabBar({ items }: { items: NavItem[] }) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Điều hướng chính"
      className="fixed inset-x-0 bottom-0 z-40 mx-2 mb-2 flex overflow-hidden rounded-2xl border border-white/80 bg-white/90 shadow-[0_12px_36px_-12px_rgba(0,45,98,0.4)] backdrop-blur-xl pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      {items.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`relative flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] transition ${
              active ? "bg-gold-tint/70 text-gold" : "text-muted hover:bg-background/70"
            }`}
          >
            <Icon className="h-5 w-5" strokeWidth={active ? 2 : 1.75} />
            <span className={active ? "font-medium" : ""}>{item.title}</span>
          </Link>
        );
      })}
    </nav>
  );
}
