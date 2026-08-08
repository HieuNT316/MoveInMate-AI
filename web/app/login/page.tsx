"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, ClipboardList, Loader2, Mail, ShieldCheck } from "lucide-react";

import { api, writeUserId, type DemoAccount } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [accounts, setAccounts] = useState<DemoAccount[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .getDemoAccounts()
      .then(setAccounts)
      .catch(() =>
        setError("Không kết nối được backend. Chạy `uvicorn src.main:app --reload` chưa?"),
      );
  }, []);

  const signIn = async (value: string) => {
    if (!value.trim() || busy) return;
    setBusy(true);
    try {
      const profile = await api.login(value);
      writeUserId(profile.user_id);
      router.push(profile.onboarding_completed_at ? "/dashboard" : "/onboarding");
    } catch {
      setError("Email không có trong hệ thống. Tài khoản do Ban quản lý cấp.");
      setBusy(false);
    }
  };

  return (
    <main className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      {/* Brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-ink px-14 py-12 text-white lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.15]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 20%, rgba(176,141,79,0.5), transparent 40%), radial-gradient(circle at 80% 70%, rgba(176,141,79,0.35), transparent 45%)",
          }}
        />

        <div className="relative flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-gold/40 bg-gold/10">
            <Building2 className="h-5 w-5 text-gold-soft" strokeWidth={1.5} />
          </div>
          <div>
            <p className="font-display text-lg font-semibold">MoveInMate</p>
            <p className="text-[11px] uppercase tracking-[0.2em] text-gold-soft/80">
              AI Concierge
            </p>
          </div>
        </div>

        <div className="relative max-w-md">
          <p className="font-display text-4xl font-semibold leading-tight">
            Nhận nhà an tâm, đồng hành chỉn chu.
          </p>
          <p className="mt-5 text-sm leading-relaxed text-white/50">
            Trợ lý AI riêng cho cư dân — hướng dẫn thủ tục, theo dõi tiến độ và
            giải đáp mọi thắc mắc trong hành trình nhận nhà của bạn.
          </p>
        </div>

        <p className="relative text-xs text-white/30">
          © 2026 MoveInMate. Đẳng cấp trong từng trải nghiệm.
        </p>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center bg-background px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 flex flex-col items-center text-center lg:hidden">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-gold/40 bg-gold-tint">
              <Building2 className="h-6 w-6 text-gold" strokeWidth={1.5} />
            </div>
            <h1 className="font-display mt-4 text-2xl font-semibold text-ink">
              MoveInMate AI
            </h1>
          </div>

          <h2 className="font-display text-3xl font-semibold text-ink">Đăng nhập</h2>
          <p className="mt-2 text-sm text-muted">
            Tài khoản do Ban quản lý cấp. Cư dân không tự đăng ký.
          </p>

          <form
            className="mt-7 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              signIn(email);
            }}
          >
            <div>
              <label className="mb-2 block text-sm font-medium text-ink">Email</label>
              <div className="flex items-center gap-2.5 rounded-xl border border-border bg-surface px-4 py-3 focus-within:border-gold/50 focus-within:ring-1 focus-within:ring-gold/30">
                <Mail className="h-4 w-4 text-muted" strokeWidth={1.75} />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="ten.ban@moveinmate.demo"
                  className="w-full bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none"
                />
              </div>
            </div>

            {error && (
              <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={busy || !email.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-3.5 text-sm font-medium text-white transition hover:bg-ink-soft disabled:opacity-40"
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              Đăng nhập
            </button>
          </form>

          <DemoAccountList
            accounts={accounts}
            onPick={(account) => {
              setEmail(account.email);
              signIn(account.email);
            }}
          />
        </div>
      </div>
    </main>
  );
}

/**
 * ⚠️ TẠM THỜI — gỡ cùng lúc với `/auth/demo-accounts`.
 *
 * Hiển thị `checklist_total` ngay ở đây là có chủ đích: người xem demo thấy
 * ngay các hồ sơ khác nhau sinh ra số mục khác nhau, trước cả khi bấm vào.
 */
function DemoAccountList({
  accounts,
  onPick,
}: {
  accounts: DemoAccount[];
  onPick: (account: DemoAccount) => void;
}) {
  if (accounts.length === 0) return null;

  return (
    <div className="mt-8 border-t border-border pt-6">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-3.5 w-3.5 text-gold" strokeWidth={1.75} />
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted">
          Tài khoản demo — chọn để đăng nhập nhanh
        </p>
      </div>

      <div className="mt-3 space-y-2">
        {accounts.map((account) => (
          <button
            key={account.user_id}
            onClick={() => onPick(account)}
            className="flex w-full items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-left transition hover:border-gold/50"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-ink">
                {account.full_name}
              </p>
              <p className="mt-0.5 truncate text-xs text-muted">{account.summary}</p>
            </div>

            {account.role === "resident" && (
              <span className="flex shrink-0 items-center gap-1.5 rounded-full border border-gold/40 bg-gold-tint px-2.5 py-1 text-[11px] text-ink">
                <ClipboardList className="h-3 w-3 text-gold" strokeWidth={2} />
                {account.checklist_total} mục
              </span>
            )}
          </button>
        ))}
      </div>

      <p className="mt-4 text-[11px] leading-relaxed text-muted">
        Bản demo chưa kiểm mật khẩu — đăng nhập chỉ tra theo email. Supabase Auth
        sẽ thay phần này.
      </p>
    </div>
  );
}
