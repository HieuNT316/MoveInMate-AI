"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bell,
  CircleUserRound,
  Gauge,
  Lock,
  PieChart,
  Search,
  UserPlus,
  UserRound,
  UserRoundX,
} from "lucide-react";

import { api, describeError, type Dashboard, type ResidentProgress } from "../../../lib/api";
import { useDemoUser } from "../../../lib/useDemoUser";
import CreateResidentDialog from "../../components/CreateResidentDialog";

const ATTENTION_THRESHOLD = 30;

export default function BQLDashboardPage() {
  const { userId, ready } = useDemoUser();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [query, setQuery] = useState("");

  const load = useCallback(async () => {
    try {
      setDashboard(await api.getDashboard(userId));
      setError(null);
    } catch (err) {
      setError(describeError(err));
    }
  }, [userId]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  const filtered = useMemo(() => {
    if (!dashboard) return [];
    const q = query.trim().toLowerCase();
    if (!q) return dashboard.residents;
    return dashboard.residents.filter(
      (r) => r.full_name.toLowerCase().includes(q) || r.apartment.toLowerCase().includes(q),
    );
  }, [dashboard, query]);

  if (error) {
    return (
      <p className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
        {error}
      </p>
    );
  }

  if (!dashboard) {
    return (
      <div className="flex items-center gap-2 text-sm text-[#64748B]">
        <Activity className="h-4 w-4 animate-pulse" />
        Đang tải danh sách cư dân...
      </div>
    );
  }

  const { total_residents } = dashboard;
  const avgPercent = dashboard.residents.length
    ? Math.round(
        dashboard.residents.reduce((sum, r) => sum + r.bql_scope.percent, 0) /
          dashboard.residents.length,
      )
    : 0;
  const notOnboarded = dashboard.residents.filter((r) => !r.onboarded).length;
  const needsAttention = dashboard.residents
    .filter((r) => r.onboarded && r.bql_scope.percent < ATTENTION_THRESHOLD)
    .sort((a, b) => a.bql_scope.percent - b.bql_scope.percent);

  return (
    <>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="relative w-full max-w-xs">
          <Search
            className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#94A3B8]"
            strokeWidth={1.75}
          />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm cư dân..."
            className="w-full rounded-lg border border-[#E2E8F0] bg-white py-2.5 pl-10 pr-3 text-sm text-[#1E293B] placeholder:text-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/15"
          />
        </div>

        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#1D4ED8]"
        >
          <UserPlus className="h-4 w-4" strokeWidth={1.75} />
          Tạo tài khoản cư dân
        </button>
      </div>

      {creating && (
        <CreateResidentDialog
          userId={userId}
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            load();
          }}
        />
      )}

      <section className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Tổng cư dân" value={String(total_residents)} icon={CircleUserRound} />
        <Stat label="Tiến độ TB onboarding" value={`${avgPercent}%`} icon={Gauge} />
        <Stat
          label="Chưa thiết lập hồ sơ"
          value={String(notOnboarded)}
          icon={UserRoundX}
          alert={notOnboarded > 0}
        />
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Cột trái — dữ liệu thật, chiếm 2/3 */}
        <div className="space-y-6 lg:col-span-2">
          {/* Ẩn khi đang tìm kiếm — thẻ này không lọc theo `query`, để nguyên
              sẽ chắn ngang kết quả tìm kiếm bên dưới, không hợp lý. */}
          {!query.trim() && needsAttention.length > 0 && (
            <Card>
              <div className="mb-4 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-[#B45309]" strokeWidth={1.75} />
                <h2 className="text-sm font-semibold text-[#1E293B]">Cư dân cần hỗ trợ</h2>
                <span className="ml-auto text-xs text-[#94A3B8]">
                  Tiến độ dưới {ATTENTION_THRESHOLD}%
                </span>
              </div>
              <div className="space-y-2">
                {needsAttention.map((r) => (
                  <ResidentRow key={r.user_id} resident={r} tone="alert" />
                ))}
              </div>
            </Card>
          )}

          <Card padded={false}>
            <div className="flex items-center gap-2 border-b border-[#E2E8F0] px-6 py-4">
              <h2 className="text-sm font-semibold text-[#1E293B]">Tất cả cư dân</h2>
              <span className="text-xs text-[#94A3B8]">({filtered.length})</span>
            </div>
            {filtered.length === 0 ? (
              <p className="px-6 py-8 text-center text-sm text-[#94A3B8]">
                Không tìm thấy cư dân khớp &quot;{query}&quot;.
              </p>
            ) : (
              <div className="divide-y divide-[#E2E8F0]">
                {filtered.map((r) => (
                  <ResidentRow key={r.user_id} resident={r} tone="neutral" />
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Cột phải — Phase 2, chưa có API tổng hợp riêng nên chỉ hiện khung
            "Sắp có", không vẽ số liệu bịa. */}
        <div className="space-y-6">
          <ComingSoonCard
            icon={PieChart}
            title="Phân bố onboarding"
            description="Biểu đồ tỉ lệ Mới / Đang điền / Chờ duyệt / Hoàn tất — cần endpoint tổng hợp riêng, chưa có ở backend."
          />
          <ComingSoonCard
            icon={Bell}
            title="Nhật ký hoạt động AI"
            description="Lịch sử agent tự nhắc việc / định tuyến yêu cầu — thuộc Phase 2 (US-11), chưa code."
          />
        </div>
      </div>
    </>
  );
}

function ResidentRow({
  resident,
  tone,
}: {
  resident: ResidentProgress;
  tone: "alert" | "neutral";
}) {
  const barColor = tone === "alert" ? "bg-rose-400" : "bg-[#2563EB]";
  return (
    <div className="flex items-center gap-4 px-6 py-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#EFF6FF]">
        <UserRound className="h-4 w-4 text-[#2563EB]" strokeWidth={1.75} />
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-[#1E293B]">
          {resident.full_name}
          <span className="ml-1.5 font-normal text-[#94A3B8]">— {resident.apartment}</span>
        </p>
        {!resident.onboarded ? (
          <p className="mt-0.5 text-xs text-[#B45309]">Chưa thiết lập hồ sơ</p>
        ) : (
          <p className="mt-0.5 text-xs text-[#94A3B8]">
            {resident.ownership_type === "owner"
              ? "Chủ hộ"
              : resident.ownership_type === "renter"
                ? "Người thuê"
                : "—"}
          </p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <div className="h-1.5 w-24 rounded-full bg-[#E2E8F0]">
          <div
            className={`h-1.5 rounded-full ${barColor}`}
            style={{ width: `${resident.bql_scope.percent}%` }}
          />
        </div>
        <span className="w-9 text-right text-xs font-semibold text-[#475569]">
          {resident.bql_scope.percent}%
        </span>
      </div>

      <button
        disabled
        title="Sắp có — cần agent tự nhắc việc (Phase 2)"
        className="flex shrink-0 cursor-not-allowed items-center gap-1.5 rounded-lg border border-[#E2E8F0] px-2.5 py-1.5 text-[11px] text-[#94A3B8]"
      >
        <Lock className="h-3 w-3" strokeWidth={2} />
        Gửi AI nhắc việc
      </button>
    </div>
  );
}

function Stat({
  label,
  value,
  icon: Icon,
  alert,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  alert?: boolean;
}) {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-5 shadow-sm shadow-slate-200/50">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-[#64748B]">{label}</p>
        <Icon
          className={`h-4 w-4 ${alert ? "text-rose-500" : "text-[#2563EB]"}`}
          strokeWidth={1.75}
        />
      </div>
      <p className="mt-2 text-2xl font-semibold text-[#1E293B]">{value}</p>
    </div>
  );
}

function Card({
  children,
  padded = true,
}: {
  children: React.ReactNode;
  padded?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border border-[#E2E8F0] bg-white shadow-sm shadow-slate-200/50 ${padded ? "p-6" : ""}`}
    >
      {children}
    </div>
  );
}

function ComingSoonCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-dashed border-[#CBD5E1] bg-[#F8FAFC] p-6">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-[#94A3B8]" strokeWidth={1.75} />
        <h3 className="text-sm font-semibold text-[#475569]">{title}</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[10px] text-[#94A3B8] ring-1 ring-[#E2E8F0]">
          <Lock className="h-2.5 w-2.5" strokeWidth={2} />
          Sắp có
        </span>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-[#94A3B8]">{description}</p>
    </div>
  );
}
