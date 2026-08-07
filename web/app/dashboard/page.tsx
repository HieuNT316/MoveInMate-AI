import Layout from "../components/Layout";
import DashboardCard from "../components/DashboardCard";
import {
  Bot,
  ClipboardList,
  UserRound,
  MessagesSquare,
  Gauge,
  BadgeCheck,
} from "lucide-react";

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

const stats = [
  { label: "Câu hỏi AI", value: "18", icon: MessagesSquare },
  { label: "Checklist & Tiến độ", value: "2/6 · 33%", icon: Gauge, tone: "text-gold", small: true },
  { label: "Trạng thái", value: "Đang nhận nhà", icon: BadgeCheck, tone: "text-emerald", small: true },
];

export default function DashboardPage() {
  return (
    <Layout>
      {/* Hero */}
      <section className="mb-10 flex flex-col justify-between gap-4 border-b border-border pb-8 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-gold">
            Xin chào
          </p>
          <h1 className="font-display mt-2 text-4xl font-semibold text-ink">
            Minh Thu
          </h1>
          <p className="mt-2 text-muted">
            Chào mừng bạn quay trở lại MoveInMate AI — hành trình nhận nhà của bạn đang tiến triển tốt.
          </p>
        </div>
      </section>

      {/* Statistics */}
      <section className="mb-10 grid grid-cols-1 gap-5 sm:grid-cols-3">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="rounded-2xl border border-border bg-surface p-6"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted">{stat.label}</p>
              <stat.icon
                className={`h-4 w-4 ${stat.tone ?? "text-ink/40"}`}
                strokeWidth={1.75}
              />
            </div>
            <h2
              className={`font-display mt-3 font-semibold text-ink ${
                stat.small ? "text-xl" : "text-3xl"
              } ${stat.tone ?? ""}`}
            >
              {stat.value}
            </h2>
          </div>
        ))}
      </section>

      {/* Feature */}
      <section>
        <div className="mb-6 flex items-center justify-between">
          <h2 className="font-display text-2xl font-semibold text-ink">
            Chức năng
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((item) => (
            <DashboardCard
              key={item.title}
              title={item.title}
              icon={item.icon}
              desc={item.desc}
              href={item.href}
              accent={item.accent}
            />
          ))}
        </div>
      </section>
    </Layout>
  );
}
