"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, Lock } from "lucide-react";

import LogoMark from "../components/LogoMark";
import { supabase } from "../../lib/supabase";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = password.length >= 8 && password === confirm;

  const submit = async () => {
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    const { error: updateError } = await supabase.auth.updateUser({ password });
    if (updateError) {
      setError(updateError.message.includes("session") ? "Liên kết đã hết hạn. Hãy yêu cầu một liên kết mới." : updateError.message);
      setBusy(false);
      return;
    }
    await supabase.auth.signOut().catch(() => undefined);
    router.replace("/login");
  };

  return <main className="flex min-h-[100dvh] items-center justify-center bg-background px-4 py-10">
    <div className="w-full max-w-md rounded-2xl border border-border bg-white p-6 shadow-xl sm:p-8">
      <div className="mb-6 flex flex-col items-center text-center"><LogoMark size={64} /><h1 className="mt-4 font-display text-2xl font-semibold text-ink">Đặt mật khẩu mới</h1><p className="mt-2 text-sm text-muted">Mật khẩu cần có ít nhất 8 ký tự.</p></div>
      <div className="space-y-4">
        <label className="block"><span className="mb-2 block text-sm font-medium text-ink">Mật khẩu mới</span><div className="flex items-center gap-2 rounded-xl border border-border px-4 py-3 focus-within:border-blue-500"><Lock className="h-4 w-4 text-muted" /><input type={show ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} className="min-w-0 flex-1 bg-transparent text-sm outline-none" /><button type="button" onClick={() => setShow((value) => !value)} aria-label={show ? "Ẩn mật khẩu" : "Hiện mật khẩu"}>{show ? <EyeOff className="h-4 w-4 text-muted" /> : <Eye className="h-4 w-4 text-muted" />}</button></div></label>
        <label className="block"><span className="mb-2 block text-sm font-medium text-ink">Nhập lại mật khẩu</span><input type={show ? "text" : "password"} value={confirm} onChange={(event) => setConfirm(event.target.value)} className="w-full rounded-xl border border-border px-4 py-3 text-sm outline-none focus:border-blue-500" /></label>
        {confirm && password !== confirm && <p className="text-xs text-red-600">Hai mật khẩu chưa khớp.</p>}
        {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <button type="button" onClick={() => void submit()} disabled={!valid || busy} className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-3.5 text-sm font-semibold text-white disabled:opacity-40">{busy && <Loader2 className="h-4 w-4 animate-spin" />}Lưu mật khẩu mới</button>
      </div>
    </div>
  </main>;
}
