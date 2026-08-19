"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bell,
  CircleUserRound,
  Gauge,
  HelpCircle,
  Lock,
  PieChart,
  UserCheck,
  UserRound,
  UserRoundX,
} from "lucide-react";

import { api, describeError, type Dashboard, type ResidentProgress } from "../../../lib/api";
import { useDemoUser } from "../../../lib/useDemoUser";

const ATTENTION_THRESHOLD = 30;

export default function BQLDashboardPage() {
  const { userId, ready } = useDemoUser();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  if (error) {
    return (
      <p className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
        {error}
      </p>
    );
  }

  if (!dashboard) {
    return (
      <div className="flex items-center gap-2 text-sm text-[#475569]">
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
  // "Hoàn tất thủ tục" = đã tick xong 100% checklist thuộc phạm vi BQL —
  // không phải đã nộp/được duyệt hồ sơ, đó là khái niệm khác (xem /bql/applications).
  const completedCount = dashboard.residents.filter(
    (r) => r.onboarded && r.bql_scope.percent === 100,
  ).length;
  const needsAttention = dashboard.residents
    .filter((r) => r.onboarded && r.bql_scope.percent < ATTENTION_THRESHOLD)
    .sort((a, b) => a.bql_scope.percent - b.bql_scope.percent);

  return (
    <>
      <div className="mb-6 flex justify-end">
        <Link
          href="/bql/residents"
          className="flex items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#1D4ED8]"
        >
          Quản lý cư dân
          <ArrowRight className="h-4 w-4" strokeWidth={1.75} />
        </Link>
      </div>

      <section className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Tổng cư dân"
          value={String(total_residents)}
          icon={CircleUserRound}
          href="/bql/residents"
          hint="Tổng số tài khoản cư dân đã tạo, không phân biệt đã điền hồ sơ hay chưa."
        />
        <Stat
          label="Tiến độ TB onboarding"
          value={`${avgPercent}%`}
          icon={Gauge}
          href="/bql/residents"
          hint="Trung bình % checklist (thuộc phạm vi BQL) đã tick xong, tính trên tất cả cư dân — kể cả người chưa điền hồ sơ (0%)."
        />
        <Stat
          label="Đã hoàn tất thủ tục"
          value={String(completedCount)}
          icon={UserCheck}
          href="/bql/residents?filter=completed"
          hint="Số cư dân đã điền hồ sơ VÀ tick xong 100% checklist BQL. Không tính hồ sơ đã được duyệt — đó là số liệu bên trang Quản lý đơn."
        />
        <Stat
          label="Chưa thiết lập hồ sơ"
          value={String(notOnboarded)}
          icon={UserRoundX}
          alert={notOnboarded > 0}
          href="/bql/residents?filter=not_onboarded"
          hint="Cư dân có tài khoản nhưng chưa điền form onboarding — checklist của họ vì vậy chưa hiện ra được."
        />
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Cột trái — dữ liệu thật, chiếm 2/3 */}
        <div className="space-y-6 lg:col-span-2">
          <Card padded={false}>
            <div className="border-b border-[#B6C4D6] px-6 py-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-[#B45309]" strokeWidth={1.75} />
                <h2 className="text-sm font-semibold text-[#1E293B]">Cư dân cần hỗ trợ</h2>
                <span className="ml-auto text-xs text-[#64748B]">
                  Tiến độ dưới {ATTENTION_THRESHOLD}%
                </span>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-[#64748B]">
                Đã điền hồ sơ onboarding nhưng còn nhiều mục checklist chưa tick
                xong — có thể đang vướng giấy tờ hoặc chưa nộp hồ sơ cho BQL. Bấm
                &quot;Xem đơn&quot; để biết cụ thể cư dân đã nộp gì, còn thiếu gì, rồi
                liên hệ nhắc trực tiếp (gọi/nhắn).
              </p>
            </div>
            {needsAttention.length === 0 ? (
              <p className="px-6 py-8 text-center text-sm text-[#64748B]">
                Không có cư dân nào cần hỗ trợ ngay.
              </p>
            ) : (
              <div className="divide-y divide-[#B6C4D6]">
                {needsAttention.slice(0, 6).map((r) => (
                  <ResidentRow key={r.user_id} resident={r} tone="alert" />
                ))}
              </div>
            )}
            <div className="border-t border-[#B6C4D6] px-6 py-3">
              <Link
                href="/bql/residents"
                className="flex items-center gap-1.5 text-xs font-medium text-[#2563EB] hover:text-[#1D4ED8]"
              >
                Xem toàn bộ danh sách cư dân
                <ArrowRight className="h-3 w-3" strokeWidth={1.75} />
              </Link>
            </div>
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
          <span className="ml-1.5 font-normal text-[#64748B]">— {resident.apartment}</span>
        </p>
        {!resident.onboarded ? (
          <p className="mt-0.5 text-xs text-[#B45309]">Chưa thiết lập hồ sơ</p>
        ) : (
          <p className="mt-0.5 text-xs text-[#B45309]">
            Còn {resident.bql_scope.total - resident.bql_scope.completed}/
            {resident.bql_scope.total} mục checklist chưa xong
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
        <span className="w-9 text-right text-xs font-semibold text-[#334155]">
          {resident.bql_scope.percent}%
        </span>
      </div>

      <Link
        href={`/bql/applications?resident=${resident.user_id}&name=${encodeURIComponent(resident.full_name)}`}
        className="flex shrink-0 items-center gap-1.5 rounded-lg border border-[#B6C4D6] px-2.5 py-1.5 text-[11px] text-[#334155] transition hover:border-[#2563EB]/40 hover:text-[#2563EB]"
      >
        Xem đơn
      </Link>

      <button
        disabled
        title="Sắp có — cần agent tự nhắc việc (Phase 2)"
        className="flex shrink-0 cursor-not-allowed items-center gap-1.5 rounded-lg border border-[#B6C4D6] px-2.5 py-1.5 text-[11px] text-[#64748B]"
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
  href,
  hint,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  alert?: boolean;
  href: string;
  hint: string;
}) {
  return (
    <Link
      href={href}
      className="block rounded-xl border border-[#B6C4D6] bg-white p-5 shadow-sm shadow-slate-200/50 transition hover:border-[#2563EB]/50 hover:shadow-md"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <p className="text-xs font-medium uppercase tracking-wide text-[#475569]">{label}</p>
          <span title={hint} className="shrink-0">
            <HelpCircle className="h-3 w-3 text-[#94A3B8]" strokeWidth={1.75} />
          </span>
        </div>
        <Icon
          className={`h-4 w-4 ${alert ? "text-rose-500" : "text-[#2563EB]"}`}
          strokeWidth={1.75}
        />
      </div>
      <p className="mt-2 text-2xl font-semibold text-[#1E293B]">{value}</p>
    </Link>
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
      className={`rounded-xl border border-[#B6C4D6] bg-white shadow-sm shadow-slate-200/50 ${padded ? "p-6" : ""}`}
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
    <div className="rounded-xl border border-dashed border-[#B6C4D6] bg-[#F8FAFC] p-6">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-[#64748B]" strokeWidth={1.75} />
        <h3 className="text-sm font-semibold text-[#334155]">{title}</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[10px] text-[#64748B] ring-1 ring-[#B6C4D6]">
          <Lock className="h-2.5 w-2.5" strokeWidth={2} />
          Sắp có
        </span>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-[#64748B]">{description}</p>
    </div>
  );
}
