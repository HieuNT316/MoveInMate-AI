"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  BadgeCheck,
  Bot,
  ClipboardList,
  ExternalLink,
  Gauge,
  Loader2,
  Send,
  Sparkles,
  UserRound,
  Zap,
} from "lucide-react";

import Layout from "../components/Layout";
import DashboardCard from "../components/DashboardCard";
import { api, describeError, type Checklist, type Profile } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { REQUEST_STATUS_LABEL, mockRequests } from "../../lib/mockRequests";

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
  const router = useRouter();
  const { userId, ready } = useDemoUser();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const me = await api.getProfile(userId);
      if (me.role === "admin") {
        router.replace("/bql/dashboard");
        return;
      }
      setProfile(me);
      setChecklist(await api.getChecklist(userId));
      setError(null);
    } catch (err) {
      setError(describeError(err));
    }
  }, [userId, router]);

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
        <Stat
          label="Trạng thái"
          value={profile.onboarding_completed_at ? "Đang nhận nhà" : "Chưa thiết lập hồ sơ"}
          icon={BadgeCheck}
          tone="text-emerald"
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

      {checklist && (
        <section className="mb-10 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
          <div className="flex flex-col gap-6">
            <ChecklistProgressCard checklist={checklist} />
            <UrgentTasksCard checklist={checklist} />
          </div>
          <div className="flex flex-col gap-6">
            <AiWelcomeCard name={profile.full_name} />
            <RecentRequestsCard />
          </div>
        </section>
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

function ChecklistProgressCard({ checklist }: { checklist: Checklist }) {
  const { percent, completed, total } = checklist.overall;
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (percent / 100) * circumference;

  const pending = checklist.items.filter((i) => !i.completed);
  const groups = [
    {
      label: "Hoàn tất",
      count: total - pending.length,
      dot: "bg-emerald",
    },
    {
      label: "Chờ thực hiện — Ban quản lý",
      count: pending.filter((i) => i.item_type === "bql_actionable").length,
      dot: "bg-gold",
    },
    {
      label: "Chờ thực hiện — ngoài BQL",
      count: pending.filter((i) => i.item_type === "third_party_info").length,
      dot: "bg-ink/40",
    },
  ];

  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-display text-base font-semibold text-ink">
            Checklist Onboarding
          </h3>
          <p className="mt-1 text-sm text-muted">
            Theo dõi toàn bộ thủ tục nhận nhà
          </p>
        </div>
        <Link
          href="/checklist"
          className="flex items-center gap-1 rounded-lg bg-gold-tint px-3 py-1.5 text-xs font-semibold text-gold"
        >
          Xem tất cả <ArrowRight className="h-3 w-3" strokeWidth={2.5} />
        </Link>
      </div>

      <div className="mt-6 flex items-center gap-8">
        <svg width={96} height={96} className="shrink-0">
          <circle cx={48} cy={48} r={40} fill="none" stroke="var(--border)" strokeWidth={8} />
          <circle
            cx={48}
            cy={48}
            r={40}
            fill="none"
            stroke="var(--gold)"
            strokeWidth={8}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            transform="rotate(-90 48 48)"
            className="transition-[stroke-dashoffset] duration-700"
          />
          <text
            x={48}
            y={53}
            textAnchor="middle"
            className="font-display fill-ink text-lg font-semibold"
          >
            {percent}%
          </text>
        </svg>

        <div className="flex-1 space-y-2">
          {groups.map((g) => (
            <div key={g.label} className="flex items-center gap-2.5">
              <span className={`h-2 w-2 shrink-0 rounded-full ${g.dot}`} />
              <span className="flex-1 text-sm text-muted">{g.label}</span>
              <span className="text-sm font-semibold text-ink">{g.count}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="mt-5 border-t border-border pt-4 text-xs text-muted">
        {completed}/{total} thủ tục đã hoàn tất
      </p>
    </div>
  );
}

function UrgentTasksCard({ checklist }: { checklist: Checklist }) {
  const urgent = checklist.items
    .filter((i) => !i.completed && i.item_type === "bql_actionable")
    .slice(0, 3);

  if (urgent.length === 0) return null;

  return (
    <div className="rounded-2xl border border-border bg-surface p-6">
      <div className="mb-4 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-gold-tint">
          <Zap className="h-3.5 w-3.5 text-gold" strokeWidth={2.25} />
        </span>
        <h3 className="font-display text-base font-semibold text-ink">
          Việc cần làm ngay
        </h3>
      </div>

      <ul>
        {urgent.map((item, i) => (
          <li
            key={item.id}
            className={`flex items-center gap-3 py-2.5 ${i !== urgent.length - 1 ? "border-b border-border" : ""}`}
          >
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-gold" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-ink">{item.task_name}</p>
              <p className="text-xs text-muted">{item.category}</p>
            </div>
          </li>
        ))}
      </ul>

      <Link
        href="/chat"
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-ink py-2.5 text-sm font-medium text-white transition hover:bg-ink-soft"
      >
        <Sparkles className="h-3.5 w-3.5 text-gold-soft" strokeWidth={2} />
        Nhờ AI hướng dẫn bước tiếp theo
      </Link>
    </div>
  );
}

function AiWelcomeCard({ name }: { name: string }) {
  const firstName = name.split(" ").slice(-1)[0] ?? name;
  return (
    <div className="rounded-2xl bg-ink p-5 text-white">
      <div className="flex items-center gap-2.5">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10">
          <Sparkles className="h-4 w-4 text-gold-soft" strokeWidth={2} />
        </span>
        <p className="font-display text-sm font-semibold">MoveInMate AI</p>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-white/75">
        Chào mừng, {firstName}. Tôi đã chuẩn bị checklist onboarding cá nhân
        hóa cho bạn. Sẵn sàng bắt đầu chưa?
      </p>
      <Link
        href="/chat"
        className="mt-3.5 flex items-center justify-center gap-2 rounded-lg bg-white py-2.5 text-xs font-semibold text-ink transition hover:bg-white/90"
      >
        <Send className="h-3.5 w-3.5" strokeWidth={2} />
        Bắt đầu ngay
      </Link>
    </div>
  );
}

function RecentRequestsCard() {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-display text-sm font-semibold text-ink">
          Yêu cầu gần đây
        </h3>
        <Link
          href="/requests"
          className="flex items-center gap-1 text-xs font-medium text-gold"
        >
          Tất cả <ExternalLink className="h-3 w-3" strokeWidth={2} />
        </Link>
      </div>

      <div className="space-y-2.5">
        {mockRequests.slice(0, 3).map((req) => (
          <div
            key={req.id}
            className="rounded-xl border border-border bg-background p-3"
          >
            <p className="text-xs font-medium text-ink">{req.title}</p>
            <div className="mt-1 flex items-center justify-between">
              <span className="text-[11px] text-muted">{req.department}</span>
              <span
                className={`text-[11px] font-medium ${
                  req.status === "in_review"
                    ? "text-gold"
                    : req.status === "submitted"
                      ? "text-muted"
                      : "text-emerald"
                }`}
              >
                {REQUEST_STATUS_LABEL[req.status]}
              </span>
            </div>
          </div>
        ))}
      </div>
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
