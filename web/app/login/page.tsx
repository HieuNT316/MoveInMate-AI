"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, Lock, Mail } from "lucide-react";

import Button from "../components/Button";
import { signInWithPassword } from "../../lib/session";
import { api, readUserId } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!email.trim() || !password) {
      setError("Nhập đủ email và mật khẩu.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await signInWithPassword(email.trim(), password);
      // Route thẳng theo role để khỏi phải nháy qua /dashboard rồi mới bị
      // đá tiếp sang /bql/dashboard (dashboard/page.tsx và bql/layout.tsx
      // vẫn giữ nguyên check role của họ — đây chỉ là tối ưu, không phải
      // cơ chế phân quyền duy nhất, hai nơi kia mới là chỗ chặn thật).
      //
      // ⚠️ role lấy theo user_id đang lưu ở localStorage (readUserId()),
      // KHÔNG phải theo tài khoản Supabase vừa đăng nhập — vì backend
      // (src/api/deps.py) chưa map JWT -> user_id thật. Xem DemoUserSwitcher
      // để đổi giữa BQL/chủ hộ/người thuê lúc test.
      const me = await api.getProfile(readUserId());
      router.push(me.role === "admin" ? "/bql/dashboard" : "/dashboard");
    } catch (err) {
      // Log ra console để chẩn đoán đúng nguyên nhân (email chưa confirm,
      // sai key Supabase, sai mật khẩu...) — trước đây bắt lỗi trống nên
      // mọi trường hợp đều hiện chung một câu "sai email hoặc mật khẩu",
      // rất khó debug khi tài khoản mới tạo không đăng nhập được.
      console.error("[login] đăng nhập thất bại:", err);
      const message = err instanceof Error ? err.message : "";
      setError(
        message
          ? `Đăng nhập thất bại: ${message}`
          : "Sai email hoặc mật khẩu. Kiểm tra lại, hoặc liên hệ Ban quản lý nếu chưa có tài khoản.",
      );
    } finally {
      setLoading(false);
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
              "radial-gradient(circle at 20% 20%, rgba(26,115,232,0.5), transparent 40%), radial-gradient(circle at 80% 70%, rgba(26,115,232,0.35), transparent 45%)",
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
            Truy cập không gian cư dân dành riêng cho bạn. Tài khoản do Ban
            quản lý cấp — không tự đăng ký được.
          </p>

          <form onSubmit={handleSubmit} className="mt-9 space-y-5">
            <div>
              <label htmlFor="email" className="mb-2 block text-sm font-medium text-ink">
                Email
              </label>
              <div className="flex items-center gap-2.5 rounded-xl border border-border bg-surface px-4 py-3 focus-within:border-gold/50 focus-within:ring-1 focus-within:ring-gold/30">
                <Mail className="h-4 w-4 text-muted" strokeWidth={1.75} />
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="example@gmail.com"
                  className="w-full bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="mb-2 block text-sm font-medium text-ink">
                Mật khẩu
              </label>
              <div className="flex items-center gap-2.5 rounded-xl border border-border bg-surface px-4 py-3 focus-within:border-gold/50 focus-within:ring-1 focus-within:ring-gold/30">
                <Lock className="h-4 w-4 text-muted" strokeWidth={1.75} />
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="********"
                  className="w-full bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none"
                />
              </div>
            </div>

            {error && (
              <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </p>
            )}

            <Button type="submit" size="lg" fullWidth loading={loading}>
              {loading ? "Đang đăng nhập..." : "Đăng nhập"}
            </Button>
          </form>
        </div>
      </div>
    </main>
  );
}
