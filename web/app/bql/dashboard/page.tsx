"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CircleUserRound,
  HelpCircle,
  ListChecks,
  UserCheck,
  UserRound,
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
  // "Hoàn tất thủ tục" = đã tick xong 100% checklist thuộc phạm vi BQL —
  // không phải đã nộp/được duyệt hồ sơ, đó là khái niệm khác (xem /bql/applications).
  const completedCount = dashboard.residents.filter(
    (r) => r.onboarded && r.bql_scope.percent === 100,
  ).length;
  const needsAttention = dashboard.residents
    .filter((r) => !r.onboarded || r.bql_scope.percent < ATTENTION_THRESHOLD)
    .sort((a, b) => a.bql_scope.percent - b.bql_scope.percent);
  const onboardingCount = dashboard.residents.filter(
    (r) => r.onboarded && r.bql_scope.percent >= ATTENTION_THRESHOLD && r.bql_scope.percent < 100,
  ).length;
  const completedPercent = total_residents
    ? Math.round((completedCount / total_residents) * 1000) / 10
    : 0;

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
          detail={`${dashboard.residents.filter((r) => r.onboarded).length}/${total_residents} đã thiết lập hồ sơ`}
        />
        <Stat
          label="Đã hoàn tất"
          value={String(completedCount)}
          icon={UserCheck}
          href="/bql/residents?filter=completed"
          hint="Số cư dân đã điền hồ sơ VÀ tick xong 100% checklist BQL. Không tính hồ sơ đã được duyệt — đó là số liệu bên trang Quản lý đơn."
          detail={`${completedPercent}% tổng cư dân`}
          tone="success"
        />
        <Stat
          label="Đang onboarding"
          value={String(onboardingCount)}
          icon={ListChecks}
          href="/bql/residents"
          hint="Đã thiết lập hồ sơ, đang hoàn thành checklist và chưa thuộc nhóm cần hỗ trợ ngay."
          detail={`Tiến độ trung bình toàn khu ${avgPercent}%`}
          tone="active"
        />
        <Stat
          label="Cần hỗ trợ"
          value={String(needsAttention.length)}
          icon={AlertTriangle}
          alert={needsAttention.length > 0}
          href="/bql/residents"
          hint={`Chưa thiết lập hồ sơ hoặc tiến độ checklist dưới ${ATTENTION_THRESHOLD}%.`}
          detail={needsAttention.length ? "Cần Ban quản lý kiểm tra" : "Không có việc khẩn cấp"}
          tone="alert"
        />
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card padded={false}>
            <div className="border-b border-[#B6C4D6] px-5 py-4 sm:px-6">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-[#B45309]" strokeWidth={1.75} />
                <h2 className="text-sm font-semibold uppercase tracking-[0.08em] text-[#1E293B]">Cần xử lý</h2>
                <span className="ml-auto text-xs text-[#64748B]">
                  Ưu tiên {Math.min(5, needsAttention.length)}/{needsAttention.length} cư dân
                </span>
              </div>
            </div>
            {needsAttention.length === 0 ? (
              <p className="px-6 py-8 text-center text-sm text-[#64748B]">
                Không có cư dân nào cần hỗ trợ ngay.
              </p>
            ) : (
              <div className="divide-y divide-[#B6C4D6]">
                {needsAttention.slice(0, 5).map((r) => (
                  <ResidentRow key={r.user_id} resident={r} />
                ))}
              </div>
            )}
            <div className="border-t border-[#B6C4D6] px-6 py-3">
              <Link
                href="/bql/residents"
                className="flex items-center gap-1.5 text-xs font-medium text-[#2563EB] hover:text-[#1D4ED8]"
              >
                Xem tất cả {needsAttention.length} cư dân cần hỗ trợ
                <ArrowRight className="h-3 w-3" strokeWidth={1.75} />
              </Link>
            </div>
          </Card>
        </div>

        <Card>
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#475569]">Tiến độ onboarding</p>
          <div className="mt-6 flex items-end justify-between gap-4">
            <div>
              <p className="text-4xl font-semibold text-[#1E293B]">{avgPercent}%</p>
              <p className="mt-1 text-xs text-[#64748B]">Trung bình checklist toàn khu</p>
            </div>
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#EFF6FF] text-[#2563EB]">
              <ListChecks className="h-7 w-7" strokeWidth={1.5} />
            </div>
          </div>
          <div className="mt-5 h-2.5 overflow-hidden rounded-full bg-[#E2E8F0]">
            <div className="h-full rounded-full bg-[#2563EB]" style={{ width: `${avgPercent}%` }} />
          </div>
          <dl className="mt-6 space-y-3 text-sm">
            <ProgressLine label="Đã hoàn tất" value={completedCount} tone="bg-emerald-500" />
            <ProgressLine label="Đang onboarding" value={onboardingCount} tone="bg-blue-500" />
            <ProgressLine label="Cần hỗ trợ" value={needsAttention.length} tone="bg-amber-500" />
          </dl>
          <Link href="/bql/residents" className="mt-6 flex items-center gap-1.5 text-xs font-medium text-[#2563EB] hover:text-[#1D4ED8]">
            Xem chi tiết tiến độ <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Card>
      </div>
    </>
  );
}

function ResidentRow({ resident }: { resident: ResidentProgress }) {
  return (
    <div className="px-5 py-4 sm:px-6">
      <div className="flex items-start gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#EFF6FF]">
        <UserRound className="h-4 w-4 text-[#2563EB]" strokeWidth={1.75} />
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-[#1E293B]">
          {resident.full_name}
          <span className="ml-1.5 font-normal text-[#64748B]">· Căn {resident.apartment}</span>
        </p>
        {!resident.onboarded ? (
          <p className="mt-0.5 text-xs text-[#B45309]">Chưa thiết lập hồ sơ</p>
        ) : (
          <p className="mt-0.5 text-xs text-[#B45309]">
            Chưa hoàn thành {resident.bql_scope.total - resident.bql_scope.completed}/
            {resident.bql_scope.total} thủ tục
          </p>
        )}
      </div>

      <Link
        href={`/bql/applications?resident=${resident.user_id}&name=${encodeURIComponent(resident.full_name)}`}
        className="flex shrink-0 items-center gap-1.5 rounded-lg bg-[#2563EB] px-3 py-2 text-xs font-medium text-white transition hover:bg-[#1D4ED8]"
      >
        Xem hồ sơ <ArrowRight className="h-3.5 w-3.5" />
      </Link>
      </div>
      <div className="mt-3 flex items-center gap-3 pl-12">
        <div className="h-2 flex-1 rounded-full bg-[#E2E8F0]">
          <div
            className="h-2 rounded-full bg-amber-500"
            style={{ width: `${resident.bql_scope.percent}%` }}
          />
        </div>
        <span className="w-9 text-right text-xs font-semibold text-[#334155]">
          {resident.bql_scope.percent}%
        </span>
      </div>
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
  detail,
  tone = "default",
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  alert?: boolean;
  href: string;
  hint: string;
  detail: string;
  tone?: "default" | "success" | "active" | "alert";
}) {
  return (
    <Link
      href={href}
      className="interactive-card group relative block overflow-hidden rounded-2xl border border-white/90 bg-white/95 p-5 shadow-soft ring-1 ring-[#B6C4D6]/60"
    >
      <span className="pointer-events-none absolute -right-8 -top-8 h-20 w-20 rounded-full bg-blue-100/70 blur-xl transition group-hover:scale-125" />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <p className="text-xs font-medium uppercase tracking-wide text-[#475569]">{label}</p>
          <span title={hint} className="shrink-0">
            <HelpCircle className="h-3 w-3 text-[#94A3B8]" strokeWidth={1.75} />
          </span>
        </div>
        <Icon
          className={`h-4 w-4 ${alert || tone === "alert" ? "text-rose-500" : tone === "success" ? "text-emerald-600" : "text-[#2563EB]"}`}
          strokeWidth={1.75}
        />
      </div>
      <p className="mt-2 text-2xl font-semibold text-[#1E293B]">{value}</p>
      <p className="mt-1 text-xs text-[#64748B]">{detail}</p>
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
      className={`rounded-2xl border border-white/90 bg-white/95 shadow-soft ring-1 ring-[#B6C4D6]/60 ${padded ? "p-6" : ""}`}
    >
      {children}
    </div>
  );
}

function ProgressLine({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className={`h-2 w-2 rounded-full ${tone}`} />
      <dt className="flex-1 text-[#475569]">{label}</dt>
      <dd className="font-semibold text-[#1E293B]">{value}</dd>
    </div>
  );
}
