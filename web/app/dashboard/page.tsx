"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  BellRing,
  Building2,
  Car,
  Clock3,
  Gauge,
  Loader2,
  PartyPopper,
  PhoneCall,
} from "lucide-react";

import Layout from "../components/Layout";
import { HOTLINE } from "../components/HotlineCard";
import {
  api,
  type Application,
  type Checklist,
  type Dashboard,
  type Profile,
} from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";

export default function DashboardPage() {
  const { userId, ready } = useDemoUser();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const me = await api.getProfile(userId);
      setProfile(me);
      setError(null);

      if (me.role === "admin") {
        setDashboard(await api.getDashboard(userId));
        setChecklist(null);
      } else {
        const [tasks, residentApplications] = await Promise.all([
          api.getChecklist(userId),
          api.getApplications(userId).catch(() => []),
        ]);
        setChecklist(tasks);
        setApplications(residentApplications);
        setDashboard(null);
      }
    } catch {
      setError("Không kết nối được backend. Chạy `uvicorn src.main:app --reload` chưa?");
    }
  }, [userId]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

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
          Đang tải...
        </div>
      </Layout>
    );
  }

  if (profile.role === "admin") {
    return (
      <Layout>
        <AdminView dashboard={dashboard} />
      </Layout>
    );
  }

  // Bước "hiện tại" = mục chưa hoàn thành gần đầu checklist nhất. `items`
  // lấy từ CÙNG api.getChecklist() render ở /checklist — không hardcode id
  // riêng, tránh lệch khi thêm/bớt bước sau này. Dùng chung cho cả banner
  // "Việc tiếp theo" và StatusStatCard bên dưới.
  const nextItem = checklist?.items.find((item) => !item.completed) ?? null;
  const actionRequired = applications.filter(
    (application) => application.status === "needs_info" || application.status === "rejected",
  );

  return (
    <Layout>
      <section className="relative mb-10 overflow-hidden rounded-3xl border border-white/80 bg-gradient-to-br from-[#002D62] via-[#073D80] to-[#075985] px-6 py-8 text-white shadow-[0_24px_60px_-36px_rgba(0,45,98,0.85)] sm:px-8">
        <span className="pointer-events-none absolute -right-16 -top-20 h-56 w-56 rounded-full bg-cyan-300/20 blur-3xl" />
        <span className="pointer-events-none absolute -bottom-24 left-1/3 h-48 w-48 rounded-full bg-blue-400/20 blur-3xl" />
        <p className="relative text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200">
          Xin chào
        </p>
        <h1 className="relative font-display mt-2 text-3xl font-bold tracking-[-0.03em] text-white sm:text-4xl">
          {profile.full_name}
        </h1>
        <p className="relative mt-2 text-white/75">
          {profile.building} · Căn hộ {profile.apartment}
        </p>
      </section>

      <section className="mb-10 grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Stat
          label="Tiến độ nhận nhà"
          value={checklist ? `${checklist.overall.percent}%` : "—"}
          detail={checklist ? `${checklist.overall.completed}/${checklist.overall.total} việc hoàn thành · ${checklist.overall.total - checklist.overall.completed} việc còn lại` : undefined}
          icon={Gauge}
          tone="text-gold"
        />
        <StatusStatCard
          value={profile.onboarding_completed_at ? "Đang nhận nhà" : "Chưa thiết lập hồ sơ"}
          nextItemId={nextItem?.id ?? null}
        />
      </section>

      {!profile.onboarding_completed_at && (
        <Link
          href="/onboarding"
          className="mb-10 flex items-center justify-between rounded-2xl border border-gold/40 bg-gold-tint px-6 py-5 transition hover:border-gold"
        >
          <div>
            <p className="text-sm font-medium text-ink">
              Bạn chưa thiết lập hồ sơ
            </p>
            <p className="mt-1 text-sm text-muted">
              Trả lời 4 câu hỏi ngắn để nhận checklist đúng với hoàn cảnh của bạn.
            </p>
          </div>
          <span className="text-sm font-medium text-gold">Bắt đầu →</span>
        </Link>
      )}

      {/* Đã thiết lập hồ sơ nhưng chưa rõ nên làm gì tiếp — chỉ thẳng vào
          MỘT việc cụ thể tiếp theo thay vì để cư dân tự đoán giữa 3 ô chức
          năng bên dưới. Việc "tiếp theo" lấy đúng mục chưa hoàn thành đầu
          checklist, giống cơ chế `nextItemId` của StatusStatCard. */}
      {profile.onboarding_completed_at && checklist && nextItem && (
        <Link
          href={`/checklist?item=${nextItem.id}`}
          className="interactive-card mb-10 flex items-center justify-between gap-4 overflow-hidden rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50 via-white to-cyan-50 px-6 py-5 shadow-soft"
        >
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-wide text-gold">
              Việc bạn cần làm tiếp theo
            </p>
            <p className="mt-1 truncate text-base font-medium text-ink">
              {nextItem.task_name}
            </p>
            {nextItem.description && (
              <p className="mt-1 line-clamp-2 text-sm text-muted">{nextItem.description}</p>
            )}
            {nextItem.required_documents.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-ink">Cần chuẩn bị:</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {nextItem.required_documents.slice(0, 3).map((document) => (
                    <span key={document.code} className="rounded-full border border-blue-200 bg-white px-2.5 py-1 text-[11px] text-ink">
                      {document.label}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
          <span className="flex shrink-0 items-center gap-1 rounded-xl bg-gold px-3.5 py-2 text-sm font-semibold text-white shadow-md">
            Bắt đầu <ArrowRight className="h-4 w-4" strokeWidth={2} />
          </span>
        </Link>
      )}

      {profile.onboarding_completed_at && checklist && !nextItem && (
        <div className="mb-10 flex items-center gap-4 rounded-2xl border border-emerald/30 bg-emerald/5 px-6 py-5">
          <PartyPopper className="h-6 w-6 shrink-0 text-emerald" strokeWidth={1.75} />
          <div>
            <p className="text-sm font-medium text-ink">
              Bạn đã hoàn tất toàn bộ checklist!
            </p>
            <p className="mt-1 text-sm text-muted">
              Còn thắc mắc gì về thủ tục nhận nhà? Hỏi ngay{" "}
              <Link href="/chat" className="font-medium text-gold hover:text-gold-soft">
              Trợ lý AI
              </Link>
              .
            </p>
          </div>
        </div>
      )}

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/90 bg-white/95 p-6 shadow-soft ring-1 ring-border/50">
          <div className="flex items-center gap-2">
            <BellRing className="h-4 w-4 text-gold" strokeWidth={1.75} />
            <h2 className="text-sm font-semibold uppercase tracking-[0.1em] text-ink">Thông báo dành cho bạn</h2>
          </div>
          {actionRequired.length === 0 ? (
            <div className="mt-5 rounded-xl bg-emerald-50 px-4 py-4 text-sm text-emerald-700">
              Không có hồ sơ nào đang yêu cầu bạn bổ sung.
            </div>
          ) : (
            <div className="mt-4 divide-y divide-border/70">
              {actionRequired.slice(0, 3).map((application) => (
                <Link
                  key={application.application_id}
                  href={`/checklist?item=${application.checklist_item_id}`}
                  className="group flex items-start gap-3 py-4 first:pt-1 last:pb-0"
                >
                  <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-amber-500 ring-4 ring-amber-100" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-ink">Cần bổ sung hồ sơ</p>
                    <p className="mt-0.5 text-sm text-muted">{application.task_name}</p>
                    {application.bql_note && <p className="mt-1 line-clamp-2 text-xs text-muted">BQL yêu cầu: {application.bql_note}</p>}
                  </div>
                  <ArrowRight className="mt-1 h-4 w-4 text-gold transition group-hover:translate-x-0.5" />
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-white/90 bg-white/95 p-6 shadow-soft ring-1 ring-border/50">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-gold" strokeWidth={1.75} />
            <h2 className="text-sm font-semibold uppercase tracking-[0.1em] text-ink">Thông tin khu nhà</h2>
          </div>
          <dl className="mt-5 grid grid-cols-2 gap-x-5 gap-y-4 text-sm">
            <HomeInfo label="Tòa" value={profile.building} />
            <HomeInfo label="Căn hộ" value={profile.apartment} />
            <HomeInfo icon={Car} label="Đăng ký xe" value={profile.has_car ? "Có" : "Không"} />
            <HomeInfo icon={Clock3} label="Văn phòng BQL" value="08:00–12:00 · 13:00–17:00" />
          </dl>
          <a
            href={`tel:${HOTLINE.number.replace(/\s/g, "")}`}
            className="mt-5 flex items-center justify-between rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm transition hover:border-gold/50"
          >
            <span className="flex items-center gap-2 text-muted"><PhoneCall className="h-4 w-4 text-gold" />Hotline BQL</span>
            <span className="font-semibold text-ink">{HOTLINE.number}</span>
          </a>
        </div>
      </section>
    </Layout>
  );
}

function HomeInfo({
  label,
  value,
  icon: Icon = Building2,
}: {
  label: string;
  value: string;
  icon?: React.ComponentType<{ className?: string; strokeWidth?: number }>;
}) {
  return (
    <div className="min-w-0 rounded-xl bg-background/75 p-3.5">
      <dt className="flex items-center gap-1.5 text-xs text-muted"><Icon className="h-3.5 w-3.5 text-gold" />{label}</dt>
      <dd className="mt-1 break-words font-semibold text-ink">{value}</dd>
    </div>
  );
}

function AdminView({ dashboard }: { dashboard: Dashboard | null }) {
  if (!dashboard) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Đang tải danh sách cư dân...
      </div>
    );
  }

  return (
    <>
      <section className="mb-8 border-b border-border pb-6">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-gold">
          Ban quản lý
        </p>
        <h1 className="font-display mt-2 text-3xl font-semibold text-ink">
          Tiến độ onboarding cư dân
        </h1>
        <p className="mt-2 text-sm text-muted">
          {dashboard.total_residents} cư dân · chỉ tính thủ tục thuộc phạm vi Ban
          quản lý xử lý
        </p>
      </section>

      <div className="overflow-hidden rounded-2xl border border-border bg-surface shadow-soft">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[32rem] text-sm">
          <thead className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-6 py-4 font-medium">Cư dân</th>
              <th className="px-6 py-4 font-medium">Căn hộ</th>
              <th className="px-6 py-4 font-medium">Loại</th>
              <th className="px-6 py-4 font-medium">Tiến độ</th>
            </tr>
          </thead>
          <tbody>
            {dashboard.residents.map((resident) => (
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
      </div>
    </>
  );
}

/**
 * Ô "Trạng thái" ở Tổng quan — thêm nút "Xem lộ trình →" trỏ sang Checklist
 * kèm `?item=<id>`, tái dùng đúng cơ chế tự cuộn + highlight mà `/checklist`
 * đã có sẵn cho nút "Đến mục này" trong chat (`checklist/page.tsx`), không
 * phải cơ chế mới. Không có bước nào dở dang (`nextItemId` null, vd đã xong
 * hết checklist) thì ẩn nút — không đưa tới id không tồn tại.
 */
function StatusStatCard({
  value,
  nextItemId,
}: {
  value: string;
  nextItemId: number | null;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface shadow-soft p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">Trạng thái</p>
        <BadgeCheck className="h-4 w-4 text-emerald" strokeWidth={1.75} />
      </div>
      <h2 className="font-display mt-3 text-xl font-semibold text-emerald">{value}</h2>

      {nextItemId !== null && (
        <Link
          href={`/checklist?item=${nextItemId}`}
          className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-gold transition hover:text-gold-soft"
        >
          Xem lộ trình →
        </Link>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  icon: Icon,
  tone,
  detail,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  tone: string;
  detail?: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface shadow-soft p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">{label}</p>
        <Icon className={`h-4 w-4 ${tone}`} strokeWidth={1.75} />
      </div>
      <h2 className={`font-display mt-3 text-xl font-semibold ${tone}`}>
        {value}
      </h2>
      {detail && <p className="mt-1.5 text-xs text-muted">{detail}</p>}
    </div>
  );
}
