import Link from "next/link";
import { Building2, Lock, Mail } from "lucide-react";

export default function LoginPage() {
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
      <div className="flex items-center justify-center bg-background px-6 py-16">
        <div className="w-full max-w-md">
          <div className="mb-10 flex flex-col items-center text-center lg:hidden">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-gold/40 bg-gold-tint">
              <Building2 className="h-6 w-6 text-gold" strokeWidth={1.5} />
            </div>
            <h1 className="font-display mt-4 text-2xl font-semibold text-ink">
              MoveInMate AI
            </h1>
          </div>

          <h2 className="font-display text-3xl font-semibold text-ink">
            Đăng nhập
          </h2>
          <p className="mt-2 text-sm text-muted">
            Truy cập không gian cư dân dành riêng cho bạn.
          </p>

          <div className="mt-9 space-y-5">
            <div>
              <label className="mb-2 block text-sm font-medium text-ink">
                Email
              </label>
              <div className="flex items-center gap-2.5 rounded-xl border border-border bg-surface px-4 py-3 focus-within:border-gold/50 focus-within:ring-1 focus-within:ring-gold/30">
                <Mail className="h-4 w-4 text-muted" strokeWidth={1.75} />
                <input
                  type="email"
                  placeholder="example@gmail.com"
                  className="w-full bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-ink">
                Mật khẩu
              </label>
              <div className="flex items-center gap-2.5 rounded-xl border border-border bg-surface px-4 py-3 focus-within:border-gold/50 focus-within:ring-1 focus-within:ring-gold/30">
                <Lock className="h-4 w-4 text-muted" strokeWidth={1.75} />
                <input
                  type="password"
                  placeholder="********"
                  className="w-full bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none"
                />
              </div>
            </div>

            <Link
              href="/dashboard"
              className="flex w-full items-center justify-center rounded-xl bg-ink py-3.5 text-sm font-medium text-white transition hover:bg-ink-soft"
            >
              Đăng nhập
            </Link>

            <div className="text-center">
              <a href="#" className="text-sm text-gold hover:text-gold/80">
                Quên mật khẩu?
              </a>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
