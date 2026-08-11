"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Car, Check, Home, KeyRound, Sparkles } from "lucide-react";

import Layout from "../components/Layout";
import Button from "../components/Button";
import {
  api,
  type AmenityPackage,
  type ApartmentType,
  type OwnershipType,
} from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";

const OWNERSHIP: { value: OwnershipType; label: string; hint: string }[] = [
  {
    value: "owner",
    label: "Tôi là chủ căn hộ",
    hint: "Nhận bàn giao từ chủ đầu tư",
  },
  {
    value: "renter",
    label: "Tôi thuê căn hộ",
    hint: "Thuê lại từ chủ sở hữu",
  },
];

const APARTMENTS: { value: ApartmentType; label: string }[] = [
  { value: "studio", label: "Studio" },
  { value: "1pn", label: "1 phòng ngủ" },
  { value: "2pn", label: "2 phòng ngủ" },
  { value: "3pn", label: "3 phòng ngủ" },
  { value: "duplex", label: "Duplex" },
];

const AMENITIES: { value: AmenityPackage; label: string }[] = [
  { value: "pool", label: "Hồ bơi" },
  { value: "gym", label: "Phòng gym" },
  { value: "tennis", label: "Sân tennis" },
  { value: "bbq", label: "Khu BBQ" },
  { value: "kids_area", label: "Khu vui chơi trẻ em" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const { userId, ready } = useDemoUser();

  const [ownership, setOwnership] = useState<OwnershipType | null>(null);
  const [apartment, setApartment] = useState<ApartmentType | null>(null);
  const [hasCar, setHasCar] = useState<boolean | null>(null);
  const [amenities, setAmenities] = useState<AmenityPackage[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const complete = ownership !== null && apartment !== null && hasCar !== null;

  const toggleAmenity = (value: AmenityPackage) =>
    setAmenities((prev) =>
      prev.includes(value) ? prev.filter((a) => a !== value) : [...prev, value],
    );

  const submit = async () => {
    if (!complete) return;
    setSaving(true);
    setError(null);
    try {
      await api.submitOnboarding(userId, {
        ownership_type: ownership,
        apartment_type: apartment,
        has_car: hasCar,
        amenity_packages: amenities,
      });
      router.push("/checklist");
    } catch {
      setError("Không lưu được hồ sơ. Kiểm tra backend đã chạy chưa.");
      setSaving(false);
    }
  };

  return (
    <Layout>
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="rounded-2xl border border-gold/30 bg-gold-tint p-6">
          <div className="flex items-start gap-3">
            <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-gold" strokeWidth={1.75} />
            <p className="text-sm leading-relaxed text-ink">
              Bốn câu hỏi ngắn để chúng tôi lập đúng danh sách thủ tục cho hoàn
              cảnh của bạn — không phải một danh sách chung chung.
            </p>
          </div>
        </div>

        <Section icon={KeyRound} title="Bạn là chủ hộ hay người thuê?">
          <div className="grid gap-3 sm:grid-cols-2">
            {OWNERSHIP.map((option) => (
              <button
                key={option.value}
                onClick={() => setOwnership(option.value)}
                className={`rounded-xl border p-4 text-left transition ${
                  ownership === option.value
                    ? "border-gold bg-gold-tint"
                    : "border-border bg-background hover:border-gold/40"
                }`}
              >
                <p className="text-sm font-medium text-ink">{option.label}</p>
                <p className="mt-1 text-xs text-muted">{option.hint}</p>
              </button>
            ))}
          </div>
        </Section>

        <Section icon={Home} title="Loại căn hộ">
          <div className="flex flex-wrap gap-2">
            {APARTMENTS.map((option) => (
              <Chip
                key={option.value}
                active={apartment === option.value}
                onClick={() => setApartment(option.value)}
              >
                {option.label}
              </Chip>
            ))}
          </div>
        </Section>

        <Section icon={Car} title="Bạn có xe cần đăng ký chỗ gửi không?">
          <div className="flex gap-2">
            <Chip active={hasCar === true} onClick={() => setHasCar(true)}>
              Có
            </Chip>
            <Chip active={hasCar === false} onClick={() => setHasCar(false)}>
              Không
            </Chip>
          </div>
        </Section>

        <Section icon={Sparkles} title="Gói tiện ích đã đăng ký">
          <div className="flex flex-wrap gap-2">
            {AMENITIES.map((option) => (
              <Chip
                key={option.value}
                active={amenities.includes(option.value)}
                onClick={() => toggleAmenity(option.value)}
              >
                {amenities.includes(option.value) && (
                  <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                )}
                {option.label}
              </Chip>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted">Có thể chọn nhiều hoặc bỏ trống.</p>
        </Section>

        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <Button
          onClick={submit}
          disabled={!complete || !ready}
          loading={saving}
          size="lg"
          fullWidth
        >
          {saving ? "Đang tạo checklist..." : "Tạo checklist của tôi"}
        </Button>
      </div>
    </Layout>
  );
}

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <div className="mb-4 flex items-center gap-2.5">
        <Icon className="h-4 w-4 text-gold" strokeWidth={1.75} />
        <h3 className="text-sm font-medium text-ink">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm transition ${
        active
          ? "border-gold bg-gold-tint font-medium text-ink"
          : "border-border bg-background text-muted hover:border-gold/40 hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
