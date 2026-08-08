"use client";

import { useCallback, useEffect, useState } from "react";
import { BadgeCheck, Building2, Car, Home, KeyRound, Loader2, Mail } from "lucide-react";

import Layout from "../components/Layout";
import { api, type Profile } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";

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
        <p className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error}
        </p>
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
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="overflow-hidden rounded-2xl border border-border bg-surface">
          <div className="bg-ink px-8 py-10">
            <div className="flex items-center gap-5">
              <div className="flex h-20 w-20 items-center justify-center rounded-full border border-gold/40 bg-gold/15 font-display text-3xl text-gold-soft">
                {initial}
              </div>
              <div>
                <h2 className="font-display text-2xl font-semibold text-white">
                  {profile.full_name}
                </h2>
                <p className="mt-1 flex items-center gap-1.5 text-sm text-white/50">
                  <Mail className="h-3.5 w-3.5" strokeWidth={1.75} />
                  {profile.email}
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 p-8 sm:grid-cols-3">
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

        <div className="rounded-2xl border border-border bg-surface p-8">
          <h3 className="font-display mb-5 text-lg font-semibold text-ink">
            Thông tin dùng để lập checklist
          </h3>

          <dl className="space-y-4 text-sm">
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
      </div>
    </Layout>
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
    <div className="rounded-xl border border-border p-5">
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
    <div className="flex items-center justify-between gap-4">
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
