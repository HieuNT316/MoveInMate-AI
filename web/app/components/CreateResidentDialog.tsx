"use client";

import { useState } from "react";
import { Check, Copy, Loader2, X } from "lucide-react";

import { api, type CreatedUser } from "../../lib/api";

/**
 * US-00 — BQL tạo tài khoản cư dân. Mật khẩu tạm chỉ hiện đúng một lần ở
 * response `POST /admin/users` (xem docstring `CreatedUserResponse` phía
 * backend) — không có cách xem lại, nên dialog phải giữ nó trên màn hình
 * cho tới khi BQL tự đóng, không tự tắt.
 */
export default function CreateResidentDialog({
  userId,
  onClose,
  onCreated,
}: {
  userId: number;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [building, setBuilding] = useState("");
  const [apartment, setApartment] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<CreatedUser | null>(null);
  const [copied, setCopied] = useState(false);

  const complete = fullName.trim() && email.trim() && building.trim() && apartment.trim();

  const submit = async () => {
    if (!complete || saving) return;
    setSaving(true);
    setError(null);
    try {
      const user = await api.createResident(userId, {
        full_name: fullName.trim(),
        email: email.trim(),
        building: building.trim(),
        apartment: apartment.trim(),
      });
      setCreated(user);
    } catch {
      setError("Không tạo được tài khoản. Email có thể đã tồn tại.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-xl">
        {created ? (
          <>
            <h3 className="font-display text-lg font-semibold text-ink">
              Đã tạo tài khoản
            </h3>
            <p className="mt-1 text-sm text-muted">
              Chép mật khẩu tạm để bàn giao — sẽ không hiện lại được nữa.
            </p>

            <div className="mt-4 space-y-2 rounded-xl border border-border bg-background p-4 text-sm">
              <p>
                <span className="text-muted">Email:</span> {created.email}
              </p>
              <div className="flex items-center justify-between gap-3">
                <p>
                  <span className="text-muted">Mật khẩu tạm:</span>{" "}
                  <code className="font-medium text-ink">
                    {created.temporary_password}
                  </code>
                </p>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(created.temporary_password);
                    setCopied(true);
                  }}
                  className="flex shrink-0 items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs text-ink transition hover:border-gold/50"
                >
                  {copied ? (
                    <Check className="h-3.5 w-3.5 text-emerald" strokeWidth={2} />
                  ) : (
                    <Copy className="h-3.5 w-3.5" strokeWidth={1.75} />
                  )}
                  {copied ? "Đã chép" : "Chép"}
                </button>
              </div>
            </div>

            <button
              onClick={onCreated}
              className="mt-6 w-full rounded-xl bg-ink py-3 text-sm font-medium text-white transition hover:bg-ink-soft"
            >
              Xong
            </button>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <h3 className="font-display text-lg font-semibold text-ink">
                Tạo tài khoản cư dân
              </h3>
              <button
                onClick={onClose}
                aria-label="Đóng"
                className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition hover:bg-background hover:text-ink"
              >
                <X className="h-4 w-4" strokeWidth={1.75} />
              </button>
            </div>

            <div className="mt-4 space-y-3">
              <Field label="Họ tên" value={fullName} onChange={setFullName} />
              <Field label="Email" value={email} onChange={setEmail} type="email" />
              <div className="grid grid-cols-2 gap-3">
                <Field label="Toà" value={building} onChange={setBuilding} />
                <Field label="Căn hộ" value={apartment} onChange={setApartment} />
              </div>
            </div>

            {error && (
              <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </p>
            )}

            <button
              onClick={submit}
              disabled={!complete || saving}
              className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-medium text-white transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-40"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {saving ? "Đang tạo..." : "Tạo tài khoản"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-muted">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-ink focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
      />
    </label>
  );
}
