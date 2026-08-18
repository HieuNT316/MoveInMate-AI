"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  BadgeCheck,
  Bot,
  ClipboardList,
  Gauge,
  Loader2,
  UserRound,
} from "lucide-react";

import Layout from "../components/Layout";
import DashboardCard from "../components/DashboardCard";
import {
  api,
  type Checklist,
  type Dashboard,
  type Profile,
} from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";

const cards = [
  {
    title: "AI Chat",
    icon: Bot,
    desc: "Hỏi đáp thủ tục nhận nhà cùng trợ lý AI 24/7",
    href: "/chat",
    accent: "gold" as const,
  },
  {
    title: "Checklist & Tiến độ",
    icon: ClipboardList,
    desc: "Theo dõi từng bước và tiến trình bàn giao",
    href: "/checklist",
    accent: "emerald" as const,
  },
  {
    title: "Hồ sơ",
    icon: UserRound,
    desc: "Thông tin cư dân và căn hộ của bạn",
    href: "/profile",
    accent: "rose" as const,
  },
];

export default function DashboardPage() {
  const { userId, ready } = useDemoUser();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
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
        setChecklist(await api.getChecklist(userId));
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

  return (
    <Layout>
      <section className="mb-10 border-b border-border pb-8">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-gold">
          Xin chào
        </p>
        <h1 className="font-display mt-2 text-4xl font-semibold text-ink">
          {profile.full_name}
        </h1>
        <p className="mt-2 text-muted">
          {profile.building} · Căn hộ {profile.apartment}
        </p>
      </section>

      <section className="mb-10 grid grid-cols-1 gap-5 sm:grid-cols-3">
        <Stat
          label="Tiến độ chung"
          value={checklist ? `${checklist.overall.completed}/${checklist.overall.total} · ${checklist.overall.percent}%` : "—"}
          icon={Gauge}
          tone="text-gold"
        />
        <Stat
          label="Thủ tục qua Ban quản lý"
          value={checklist ? `${checklist.bql_scope.completed}/${checklist.bql_scope.total} · ${checklist.bql_scope.percent}%` : "—"}
          icon={ClipboardList}
          tone="text-ink"
        />
        <StatusStatCard
          value={profile.onboarding_completed_at ? "Đang nhận nhà" : "Chưa thiết lập hồ sơ"}
          // Bước "hiện tại" = mục chưa hoàn thành gần đầu checklist nhất.
          // `items` lấy từ CÙNG api.getChecklist() render ở /checklist —
          // không hardcode id riêng, tránh lệch khi thêm/bớt bước sau này.
          nextItemId={checklist?.items.find((item) => !item.completed)?.id ?? null}
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

      <section>
        <h2 className="font-display mb-6 text-2xl font-semibold text-ink">
          Chức năng
        </h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((item) => (
            <DashboardCard key={item.title} {...item} />
          ))}
        </div>
      </section>
    </Layout>
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
    <div className="rounded-2xl border border-border bg-surface p-6">
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
