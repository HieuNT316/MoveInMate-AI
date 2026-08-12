"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CircleUserRound,
  Gauge,
  Loader2,
  UserRoundX,
} from "lucide-react";

import { api, describeError, type Dashboard } from "../../../lib/api";
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
      <div className="flex items-center gap-2 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Đang tải danh sách cư dân...
      </div>
    );
  }

  const { residents, total_residents } = dashboard;
  const avgPercent = residents.length
    ? Math.round(
        residents.reduce((sum, r) => sum + r.bql_scope.percent, 0) /
          residents.length,
      )
    : 0;
  const notOnboarded = residents.filter((r) => !r.onboarded).length;
  const needsAttention = residents
    .filter((r) => r.onboarded && r.bql_scope.percent < ATTENTION_THRESHOLD)
    .sort((a, b) => a.bql_scope.percent - b.bql_scope.percent);

  return (
    <>
      <section className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-3">
        <Stat
          label="Tổng cư dân"
          value={String(total_residents)}
          icon={CircleUserRound}
          tone="text-ink"
        />
        <Stat
          label="Tiến độ trung bình"
          value={`${avgPercent}%`}
          icon={Gauge}
          tone="text-gold"
        />
        <Stat
          label="Chưa thiết lập hồ sơ"
          value={String(notOnboarded)}
          icon={UserRoundX}
          tone="text-rose-600"
        />
      </section>

      {needsAttention.length > 0 && (
        <section className="mb-8 rounded-2xl border border-gold/40 bg-gold-tint p-6">
          <div className="mb-4 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-gold" strokeWidth={1.75} />
            <h2 className="font-display text-base font-semibold text-ink">
              Cư dân cần hỗ trợ
            </h2>
            <span className="ml-auto text-xs text-muted">
              Tiến độ dưới {ATTENTION_THRESHOLD}%
            </span>
          </div>
          <div className="space-y-3">
            {needsAttention.map((r) => (
              <div
                key={r.user_id}
                className="flex items-center justify-between gap-4 rounded-xl border border-border bg-surface px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-ink">
                    {r.full_name}
                  </p>
                  <p className="text-xs text-muted">{r.apartment}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="h-2 w-24 rounded-full bg-border">
                    <div
                      className="h-2 rounded-full bg-rose-400"
                      style={{ width: `${r.bql_scope.percent}%` }}
                    />
                  </div>
                  <span className="w-10 text-right text-xs font-semibold text-rose-600">
                    {r.bql_scope.percent}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="font-display mb-4 text-lg font-semibold text-ink">
          Tất cả cư dân
        </h2>
        <div className="overflow-hidden rounded-2xl border border-border bg-surface">
          <table className="w-full text-sm">
            <thead className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-6 py-4 font-medium">Cư dân</th>
                <th className="px-6 py-4 font-medium">Căn hộ</th>
                <th className="px-6 py-4 font-medium">Loại</th>
                <th className="px-6 py-4 font-medium">Tiến độ</th>
              </tr>
            </thead>
            <tbody>
              {residents.map((resident) => (
                <tr
                  key={resident.user_id}
                  className="border-b border-border last:border-0"
                >
                  <td className="px-6 py-4">
                    <p className="font-medium text-ink">{resident.full_name}</p>
                    {!resident.onboarded && (
                      <p className="mt-0.5 text-xs text-gold">Chưa thiết lập hồ sơ</p>
                    )}
                  </td>
                  <td className="px-6 py-4 text-muted">{resident.apartment}</td>
                  <td className="px-6 py-4 text-muted">
                    {resident.ownership_type === "owner"
                      ? "Chủ hộ"
                      : resident.ownership_type === "renter"
                        ? "Người thuê"
                        : "—"}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="h-2 w-28 rounded-full bg-border">
                        <div
                          className="h-2 rounded-full bg-gradient-to-r from-gold to-gold-soft"
                          style={{ width: `${resident.bql_scope.percent}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted">
                        {resident.bql_scope.completed}/{resident.bql_scope.total}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function Stat({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  tone: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">{label}</p>
        <Icon className={`h-4 w-4 ${tone}`} strokeWidth={1.75} />
      </div>
      <h2 className={`font-display mt-3 text-xl font-semibold ${tone}`}>
        {value}
      </h2>
    </div>
  );
}
