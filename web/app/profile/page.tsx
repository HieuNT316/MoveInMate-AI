"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BadgeCheck,
  Building2,
  Car,
  Check,
  Home,
  KeyRound,
  Loader2,
  Lock,
  Mail,
  BellRing,
  Smartphone,
} from "lucide-react";

import Layout from "../components/Layout";
import { api, type Profile } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { supabase, supabaseConfigured } from "../../lib/supabase";
import ErrorState from "../components/ErrorState";

const AMENITY_LABELS: Record<string, string> = {
  pool: "Hồ bơi",
  gym: "Phòng gym",
  tennis: "Sân tennis",
  bbq: "Khu BBQ",
  kids_area: "Khu vui chơi trẻ em",
};

const APARTMENT_LABELS: Record<string, string> = {
  studio: "Studio",
  "1pn": "1 phòng ngủ",
  "2pn": "2 phòng ngủ",
  "3pn": "3 phòng ngủ",
  duplex: "Duplex",
};

export default function ProfilePage() {
  const { userId, ready } = useDemoUser();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setProfile(await api.getProfile(userId));
      setError(null);
    } catch {
      setError("Không kết nối được backend.");
    }
  }, [userId]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  /** Gửi đúng một field — checklist sẽ tự cập nhật theo vì được lọc trực tiếp. */
  const toggleCar = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      setProfile(await api.updateProfile(userId, { has_car: !profile.has_car }));
    } catch {
      setError("Không cập nhật được hồ sơ.");
    } finally {
      setSaving(false);
    }
  };

  if (error) {
    return (
      <Layout>
        <ErrorState message={error} onRetry={load} />
      </Layout>
    );
  }

  if (!profile) {
    return (
      <Layout>
        <div className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Đang tải hồ sơ...
        </div>
      </Layout>
    );
  }

  const initial = profile.full_name.charAt(0).toUpperCase();
  const isOwner = profile.ownership_type === "owner";

  return (
    <Layout>
      <div className="mx-auto max-w-4xl space-y-5">
        <div className="overflow-hidden rounded-2xl border border-white/90 bg-surface/95 shadow-soft ring-1 ring-border/50">
          <div className="border-b border-border bg-gradient-to-r from-white via-blue-50/40 to-cyan-50/40 px-6 py-7 sm:px-8">
            <div className="flex items-center gap-5">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-gold/30 bg-gradient-to-br from-gold to-gold-soft font-display text-2xl font-bold text-white shadow-md">
                {initial}
              </div>
              <div>
                <h2 className="font-display text-2xl font-semibold text-ink">
                  {profile.full_name}
                </h2>
                <p className="mt-1 flex items-center gap-1.5 text-sm text-muted">
                  <Mail className="h-3.5 w-3.5" strokeWidth={1.75} />
                  {profile.email}
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-3 sm:px-8">
            <Card icon={Building2} label="Tòa" value={profile.building} />
            <Card icon={Home} label="Căn hộ" value={profile.apartment} />
            <Card
              icon={BadgeCheck}
              label="Trạng thái"
              value={profile.onboarding_completed_at ? "Đang nhận nhà" : "Chưa thiết lập"}
              accent={profile.onboarding_completed_at ? "text-emerald" : "text-muted"}
            />
          </div>
        </div>

        <div className="rounded-2xl border border-white/90 bg-surface/95 p-6 shadow-soft ring-1 ring-border/50 sm:p-8">
          <h3 className="font-display mb-5 text-lg font-semibold text-ink">
            Thông tin onboarding
          </h3>

          <dl className="divide-y divide-border/70 text-sm">
            <Row
              icon={KeyRound}
              label="Hình thức sở hữu"
              value={
                profile.ownership_type
                  ? isOwner
                    ? "Chủ căn hộ"
                    : "Người thuê"
                  : "Chưa khai báo"
              }
            />
            <Row
              icon={Home}
              label="Loại căn hộ"
              value={
                profile.apartment_type
                  ? APARTMENT_LABELS[profile.apartment_type]
                  : "Chưa khai báo"
              }
            />
            <Row
              icon={Car}
              label="Có xe"
              value={profile.has_car ? "Có" : "Không"}
              action={
                <button
                  onClick={toggleCar}
                  disabled={saving}
                  className="rounded-full border border-border px-3 py-1 text-xs text-muted transition hover:border-gold/50 hover:text-gold disabled:opacity-40"
                >
                  {saving ? "Đang lưu..." : "Đổi"}
                </button>
              }
            />
          </dl>

          <div className="mt-5 border-t border-border pt-5">
            <p className="text-xs uppercase tracking-wide text-muted">
              Gói tiện ích
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {profile.amenity_packages.length === 0 ? (
                <span className="text-sm text-muted">Chưa đăng ký gói nào</span>
              ) : (
                profile.amenity_packages.map((amenity) => (
                  <span
                    key={amenity}
                    className="rounded-full border border-gold/40 bg-gold-tint px-3 py-1 text-xs text-ink"
                  >
                    {AMENITY_LABELS[amenity] ?? amenity}
                  </span>
                ))
              )}
            </div>
          </div>

          <p className="mt-5 text-xs leading-relaxed text-muted">
            Đổi thông tin ở đây thì checklist tự cập nhật ngay — danh sách được
            lọc lại mỗi lần xem, không lưu cứng lúc đăng ký.
          </p>
        </div>

        <ChangePasswordCard />
        <NotificationSettingsCard />
      </div>
    </Layout>
  );
}

function NotificationSettingsCard() {
  const supported = typeof window !== "undefined" && "Notification" in window && "serviceWorker" in navigator;
  const [permission, setPermission] = useState<NotificationPermission>(() => supported ? Notification.permission : "denied");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const enable = async () => {
    if (!supported || busy) return;
    setBusy(true);
    const result = await Notification.requestPermission();
    setPermission(result);
    setMessage(result === "granted" ? "Điện thoại đã cho phép thông báo. Hệ thống sẽ nhận push sau khi backend đăng ký thiết bị." : result === "denied" ? "Thông báo đang bị chặn trong cài đặt trình duyệt." : "Bạn chưa cấp quyền thông báo.");
    setBusy(false);
  };

  const test = async () => {
    const registration = await navigator.serviceWorker.ready;
    await registration.showNotification("MoveInMate", { body: "Thông báo trên thiết bị đang hoạt động.", icon: "/pwa/icon-192", data: { url: "/documents" } });
  };

  return <div className="rounded-2xl border border-white/90 bg-surface/95 p-6 shadow-soft ring-1 ring-border/50 sm:p-8">
    <div className="flex items-start gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600"><BellRing className="h-5 w-5" /></span><div><h3 className="font-display text-lg font-semibold text-ink">Thông báo trên điện thoại</h3><p className="mt-1 text-sm text-muted">Nhận cập nhật hồ sơ ngay cả khi không mở ứng dụng.</p></div></div>
    {!supported ? <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">Trình duyệt này chưa hỗ trợ thông báo đẩy.</p> : <div className="mt-5 flex flex-col gap-3 sm:flex-row">
      {permission !== "granted" ? <button type="button" onClick={() => void enable()} disabled={busy || permission === "denied"} className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"><Smartphone className="h-4 w-4" />{busy ? "Đang yêu cầu..." : permission === "denied" ? "Thông báo đã bị chặn" : "Cho phép thông báo"}</button> : <button type="button" onClick={() => void test()} className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-700 hover:bg-blue-100">Gửi thông báo thử</button>}
    </div>}
    {message && <p className="mt-3 text-xs leading-5 text-muted">{message}</p>}
  </div>;
}

/**
 * Đổi mật khẩu tự phục vụ — gọi thẳng `supabase.auth.updateUser()` từ trình
 * duyệt bằng phiên đang đăng nhập, không qua backend riêng nào. Khác hẳn
 * "Đặt lại mật khẩu" bên BQL (routes.py — sinh mật khẩu tạm cho người KHÁC
 * qua Supabase Admin API): ở đây cư dân tự đặt mật khẩu CỦA CHÍNH MÌNH, chỉ
 * cần đang có phiên hợp lệ, không cần mật khẩu cũ.
 */
function ChangePasswordCard() {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  if (!supabaseConfigured) return null;

  const mismatch = confirmPassword.length > 0 && newPassword !== confirmPassword;
  const tooShort = newPassword.length > 0 && newPassword.length < 8;
  const canSubmit = newPassword.length >= 8 && newPassword === confirmPassword;

  const submit = async () => {
    if (!canSubmit || saving) return;
    setSaving(true);
    setError(null);
    setDone(false);
    try {
      const { error: updateError } = await supabase.auth.updateUser({
        password: newPassword,
      });
      if (updateError) throw updateError;
      setNewPassword("");
      setConfirmPassword("");
      setDone(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không đổi được mật khẩu, thử lại sau.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-2xl border border-white/90 bg-surface/95 p-6 shadow-soft ring-1 ring-border/50 sm:p-8">
      <h3 className="font-display mb-1 text-lg font-semibold text-ink">
        Đổi mật khẩu
      </h3>
      <p className="mb-5 text-sm text-muted">
        Đổi xong sẽ không đăng xuất — dùng ngay được ở lần đăng nhập tiếp theo.
      </p>

      <div className="space-y-3 max-w-sm">
        <label className="block">
          <span className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted">
            <Lock className="h-3.5 w-3.5" strokeWidth={1.75} />
            Mật khẩu mới
          </span>
          <input
            type="password"
            value={newPassword}
            onChange={(event) => {
              setNewPassword(event.target.value);
              setDone(false);
            }}
            placeholder="Tối thiểu 8 ký tự"
            className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-ink focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
          />
          {tooShort && (
            <p className="mt-1 text-[11px] text-danger">Cần ít nhất 8 ký tự.</p>
          )}
        </label>

        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-muted">
            Nhập lại mật khẩu mới
          </span>
          <input
            type="password"
            value={confirmPassword}
            onChange={(event) => {
              setConfirmPassword(event.target.value);
              setDone(false);
            }}
            className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-ink focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
          />
          {mismatch && (
            <p className="mt-1 text-[11px] text-danger">Hai mật khẩu chưa khớp.</p>
          )}
        </label>

        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs text-red-700">
            {error}
          </p>
        )}

        {done && (
          <p className="flex items-center gap-1.5 text-xs font-medium text-emerald">
            <Check className="h-3.5 w-3.5" strokeWidth={2} />
            Đã đổi mật khẩu thành công.
          </p>
        )}

        <button
          onClick={submit}
          disabled={!canSubmit || saving}
          className="flex items-center gap-2 rounded-xl bg-ink px-5 py-2.5 text-sm font-medium text-white transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "Đang lưu..." : "Đổi mật khẩu"}
        </button>
      </div>
    </div>
  );
}

type IconType = React.ComponentType<{ className?: string; strokeWidth?: number }>;

function Card({
  icon: Icon,
  label,
  value,
  accent = "text-ink",
}: {
  icon: IconType;
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border border-border/80 bg-background/55 p-4">
      <Icon className="h-4 w-4 text-gold" strokeWidth={1.75} />
      <p className="mt-3 text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={`font-display mt-1 text-lg font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function Row({
  icon: Icon,
  label,
  value,
  action,
}: {
  icon: IconType;
  label: string;
  value: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3.5 first:pt-0 last:pb-0">
      <dt className="flex items-center gap-2.5 text-muted">
        <Icon className="h-4 w-4 text-gold" strokeWidth={1.75} />
        {label}
      </dt>
      <dd className="flex items-center gap-3 font-medium text-ink">
        {value}
        {action}
      </dd>
    </div>
  );
}
