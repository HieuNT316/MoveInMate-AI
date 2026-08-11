"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Users } from "lucide-react";

import { api, clearUserId, type DemoAccount } from "../../lib/api";
import { supabase } from "../../lib/supabase";
import { useDemoUser } from "../../lib/useDemoUser";

/**
 * ⚠️ TẠM THỜI — chỉ dành cho demo, phải gỡ khi có đăng nhập Supabase thật.
 *
 * Đổi vai ngay trên màn hình để so sánh checklist giữa các hồ sơ mà không phải
 * đăng xuất. Danh sách lấy từ `/auth/demo-accounts` chứ không hardcode id:
 * seed lại dữ liệu là danh sách tự đúng theo.
 */
export default function DemoUserSwitcher() {
  const router = useRouter();
  const { userId, switchUser, ready } = useDemoUser();
  const [accounts, setAccounts] = useState<DemoAccount[]>([]);

  useEffect(() => {
    api.getDemoAccounts().then(setAccounts).catch(() => setAccounts([]));
  }, []);

  if (accounts.length === 0) return null;

  return (
    <div className="flex items-center gap-1 rounded-full border border-gold/40 bg-gold-tint px-2 py-1.5">
      <Users className="ml-1.5 h-3.5 w-3.5 shrink-0 text-gold" strokeWidth={1.75} />
      <span className="mr-1 text-[11px] uppercase tracking-wider text-muted">Demo</span>

      {accounts.map((account) => (
        <button
          key={account.user_id}
          onClick={() => switchUser(account.user_id)}
          title={`${account.full_name} — ${account.summary}`}
          className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs transition ${
            ready && userId === account.user_id
              ? "bg-ink font-medium text-white"
              : "text-muted hover:text-ink"
          }`}
        >
          {shortLabel(account)}
        </button>
      ))}

      <button
        onClick={async () => {
          // Xoá cả phiên Supabase: chỉ xoá localStorage thì token vẫn còn và
          // lần vào sau vẫn đăng nhập như cũ.
          await supabase.auth.signOut().catch(() => undefined);
          clearUserId();
          router.push("/login");
        }}
        title="Đăng xuất"
        className="ml-1 flex h-6 w-6 items-center justify-center rounded-full text-muted transition hover:bg-white/60 hover:text-ink"
      >
        <LogOut className="h-3.5 w-3.5" strokeWidth={1.75} />
      </button>
    </div>
  );
}

/** Nhãn ngắn để nút không tràn header — chi tiết đã có ở tooltip. */
function shortLabel(account: DemoAccount): string {
  if (account.role === "admin") return "BQL";
  if (account.summary.startsWith("Chưa")) return "Mới";

  const owner = account.summary.startsWith("Chủ hộ");
  const car = account.summary.includes("có ô tô");
  return `${owner ? "Chủ hộ" : "Thuê"}${car ? " +xe" : ""} · ${account.checklist_total}`;
}
