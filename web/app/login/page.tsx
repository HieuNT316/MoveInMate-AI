"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bot,
  Building2,
  Check,
  CheckCircle2,
  ClipboardList,
  Loader2,
  Lock,
  Mail,
  Sparkles,
  UserRound,
  ShieldCheck,
} from "lucide-react";

import { api, ApiError, destinationFor, writeUserId, type DemoAccount } from "../../lib/api";
import { DEMO_PASSWORD, supabase, supabaseConfigured } from "../../lib/supabase";

// Badge số mục checklist trong danh sách tài khoản demo — xen kẽ 2 tông để
// đỡ đơn điệu khi liệt kê nhiều tài khoản liền nhau, cả hai đều đạt AA trên
// nền nhạt cùng tông (border/text/bg cùng gam nên không cần kiểm lại từng
// đôi thủ công).
const BADGE_TONES = ["border border-gold/40 bg-gold-tint text-ink", "border border-emerald/30 bg-emerald/10 text-emerald"];

const HANDOVER_STEPS = [
  { label: "Điền hồ sơ", hint: "Loại căn, xe, tiện ích", icon: ClipboardList },
  { label: "Nhận checklist", hint: "Cá nhân hoá theo hồ sơ", icon: Sparkles },
  { label: "Hoàn tất thủ tục", hint: "AI đồng hành từng bước", icon: CheckCircle2 },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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

  const signIn = async (emailValue: string, passwordValue: string) => {
    if (!emailValue.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      if (!supabaseConfigured) {
        throw new Error("Chưa cấu hình NEXT_PUBLIC_SUPABASE_URL / ANON_KEY");
      }
      const { error: authError } = await supabase.auth.signInWithPassword({
        email: emailValue.trim(),
        password: passwordValue,
      });
      if (authError) throw authError;

      // Lấy hồ sơ cư dân bằng chính token vừa nhận — `getProfile` tự gắn Bearer.
      // `writeUserId` chỉ còn để bộ đổi persona của bản demo biết đang là ai.
      const profile = await api.getProfile(0);
      writeUserId(profile.user_id);
      router.push(destinationFor(profile));
    } catch (err) {
      // 403 ở đây nghĩa là: đăng nhập Supabase thành công (đúng mật khẩu),
      // nhưng chưa có hồ sơ cư dân gắn với tài khoản này — khác hẳn "sai mật
      // khẩu", nên cần thông báo riêng, không rơi vào nhánh "credentials".
      if (err instanceof ApiError && err.status === 403) {
        setError(
          "Tài khoản này chưa được Ban quản lý gán hồ sơ cư dân. Thử một tài khoản demo bên dưới, hoặc liên hệ BQL để được cấp hồ sơ.",
        );
        setBusy(false);
        return;
      }
      const message = err instanceof Error ? err.message : "";
      setError(
        message.toLowerCase().includes("credentials")
          ? "Email hoặc mật khẩu không đúng. Tài khoản do Ban quản lý cấp."
          : message || "Không đăng nhập được.",
      );
      setBusy(false);
    }
  };

  return (
    <main className="grid min-h-screen grid-cols-1 lg:h-screen lg:grid-cols-2">
      {/* Brand panel — cố định, không cuộn theo form bên phải */}
      <div
        className="relative hidden flex-col justify-between overflow-hidden px-14 py-12 text-white lg:flex lg:h-screen"
        style={{ background: "linear-gradient(180deg, #0A192F 0%, #1E3A8A 100%)" }}
      >
        {/* Ảnh khu dân cư — mờ nhoè, chỉ để gợi không khí, không được ăn chữ.
            Ảnh miễn phí bản quyền (Unsplash License), không phải ảnh thật của
            Vinhomes — tránh dùng ảnh marketing có bản quyền của bên khác. */}
        <div
          className="pointer-events-none absolute inset-0 bg-cover bg-center opacity-[0.4] saturate-[0.85]"
          style={{ backgroundImage: "url(/login-skyline.jpg)" }}
        />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#0A192F]/60 via-[#0A192F]/55 to-[#1E3A8A]/90" />
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

        {/* Mascot — chào mừng bằng AI, đặt trước phần headline để ấn tượng
            đầu tiên là "có trợ lý đồng hành", không phải một cái form trơ. */}
        <div className="relative flex items-start gap-3.5">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-gold/30 to-gold/5 ring-1 ring-gold/30">
            <Bot className="h-7 w-7 text-gold-soft" strokeWidth={1.5} />
          </div>
          <div className="relative max-w-[19rem] rounded-2xl rounded-tl-sm border border-white/15 bg-white/10 px-4 py-3 text-sm leading-relaxed text-white/85 shadow-lg backdrop-blur-md">
            Chào mừng bạn đến với nhà mới! Tôi là MoveInMate AI, trợ lý riêng
            của bạn — đừng lo về thủ tục, tôi sẽ hướng dẫn từng bước.
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

          <ol className="mt-8 flex items-center gap-2 rounded-2xl border border-white/15 bg-white/[0.08] p-4 shadow-lg backdrop-blur-md">
            {HANDOVER_STEPS.map((step, index) => (
              <li key={step.label} className="flex flex-1 items-center gap-2">
                <div className="flex flex-1 items-start gap-2.5">
                  <div
                    className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                      index === 0
                        ? "bg-gold text-ink shadow-[0_0_10px_2px_rgba(0,86,210,0.55)]"
                        : index === 1
                          ? "border-2 border-gold-soft text-gold-soft shadow-[0_0_8px_1px_rgba(26,115,232,0.5)]"
                          : "border border-dashed border-white/30 text-white/50"
                    }`}
                  >
                    {index === 0 ? (
                      <Check className="h-3.5 w-3.5" strokeWidth={3} />
                    ) : (
                      <step.icon className="h-3 w-3" strokeWidth={2} />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-white/85">{step.label}</p>
                    <p className="mt-0.5 text-[11px] leading-snug text-white/40">
                      {step.hint}
                    </p>
                  </div>
                </div>
                {index !== HANDOVER_STEPS.length - 1 && (
                  <div className="h-px w-6 shrink-0 bg-white/15" />
                )}
              </li>
            ))}
          </ol>
        </div>

        <p className="relative text-xs text-white/30">
          © 2026 MoveInMate. Đẳng cấp trong từng trải nghiệm.
        </p>
      </div>

      {/* Form panel — khối ngoài chỉ định vị nền (không cuộn); khối trong mới
          cuộn riêng khi danh sách tài khoản demo dài hơn màn hình. Tách 2 lớp
          vì nền `absolute inset-0` nằm chung với `overflow-y-auto` từng làm
          lệch chiều cao cuộn, kéo xuống cuối bị hụt một đoạn. */}
      <div className="relative bg-background lg:h-screen">
        {/* Ảnh nội thất — gợi cảm giác ấm cúng, gần gũi. Form nằm trong thẻ
            đặc (bg-surface) nên ảnh phía sau có đậm hơn cũng không ăn chữ.
            Ảnh miễn phí bản quyền (Unsplash License). */}
        <div
          className="pointer-events-none absolute inset-0 bg-cover bg-center opacity-100 saturate-[1.1]"
          style={{ backgroundImage: "url(/login-interior.jpg)" }}
        />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-background/10 via-background/40 to-background" />

        {/* `items-center` (canh giữa dọc) + nội dung tràn khi cuộn là tổ hợp
            gây lỗi kinh điển: trình duyệt chia đôi phần tràn ra cả 2 phía,
            phía đầu bị cắt mất, kéo lên không thấy. Chỉ canh giữa ngang, để
            nội dung chảy tự nhiên từ trên xuống thì cuộn mới trọn vẹn. */}
        <div className="relative flex h-full justify-center overflow-y-auto px-6 py-12 lg:h-screen">
        <div className="relative w-full max-w-md self-start">
          <div className="mb-8 flex flex-col items-center text-center lg:hidden">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-gold/40 bg-gold-tint">
              <Building2 className="h-6 w-6 text-gold" strokeWidth={1.5} />
            </div>
            <h1 className="font-display mt-4 text-2xl font-semibold text-ink">
              MoveInMate AI
            </h1>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-8 shadow-xl shadow-ink/5">
            <h2 className="font-display text-3xl font-semibold text-ink">Đăng nhập</h2>
            <p className="mt-2 text-sm text-muted">
              Tài khoản do Ban quản lý cấp. Cư dân không tự đăng ký.
            </p>

            <form
              className="mt-7 space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                signIn(email, password);
              }}
            >
              <div>
                <label className="mb-2 block text-sm font-medium text-ink">Email</label>
                <div className="flex items-center gap-2.5 rounded-xl border border-border bg-background px-4 py-3 shadow-inner transition focus-within:border-gold focus-within:ring-2 focus-within:ring-gold/25">
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

              <div>
                <label className="mb-2 block text-sm font-medium text-ink">Mật khẩu</label>
                <div className="flex items-center gap-2.5 rounded-xl border border-border bg-background px-4 py-3 shadow-inner transition focus-within:border-gold focus-within:ring-2 focus-within:ring-gold/25">
                  <Lock className="h-4 w-4 text-muted" strokeWidth={1.75} />
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="••••••••"
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
                disabled={busy || !email.trim() || !password}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-gold py-3.5 text-sm font-medium text-white shadow-lg shadow-gold/25 transition hover:bg-gold-soft disabled:opacity-40 disabled:shadow-none"
              >
                {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                Đăng nhập
              </button>
            </form>
          </div>

          <DemoAccountList
            accounts={accounts}
            onPick={(account) => {
              setEmail(account.email);
              setPassword(DEMO_PASSWORD);
              signIn(account.email, DEMO_PASSWORD);
            }}
          />
        </div>
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
        {accounts.map((account, index) => {
          const badge = BADGE_TONES[index % BADGE_TONES.length];
          return (
            <button
              key={account.user_id}
              onClick={() => onPick(account)}
              className="flex w-full items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-left shadow-sm transition hover:-translate-y-px hover:border-gold/50 hover:shadow-md"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gold-tint">
                <UserRound className="h-4 w-4 text-gold" strokeWidth={1.75} />
              </div>

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink">
                  {account.full_name}
                </p>
                <p className="mt-0.5 truncate text-xs text-muted">{account.summary}</p>
              </div>

              {account.role === "resident" && (
                <span
                  className={`flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ${badge}`}
                >
                  <ClipboardList className="h-3 w-3" strokeWidth={2} />
                  {account.checklist_total} mục
                </span>
              )}
            </button>
          );
        })}
      </div>

      <p className="mt-4 text-[11px] leading-relaxed text-muted">
        Bấm để đăng nhập bằng Supabase Auth với tài khoản mẫu. Cư dân thật nhận
        mật khẩu riêng do Ban quản lý bàn giao.
      </p>
    </div>
  );
}
