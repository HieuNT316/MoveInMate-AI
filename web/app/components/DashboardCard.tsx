import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { ArrowUpRight } from "lucide-react";

type Accent = "gold" | "emerald" | "ink" | "rose";

const accents: Record<Accent, { bg: string; ring: string; icon: string }> = {
  gold: { bg: "bg-gold-tint", ring: "group-hover:ring-gold/40", icon: "text-gold" },
  emerald: { bg: "bg-emerald/10", ring: "group-hover:ring-emerald/30", icon: "text-emerald" },
  ink: { bg: "bg-ink/[0.06]", ring: "group-hover:ring-ink/20", icon: "text-ink" },
  rose: { bg: "bg-rose-50", ring: "group-hover:ring-rose-300/50", icon: "text-rose-700" },
};

type Props = {
  title: string;
  icon: LucideIcon;
  desc: string;
  href: string;
  accent: Accent;
};

export default function DashboardCard({
  title,
  icon: Icon,
  desc,
  href,
  accent,
}: Props) {
  const tone = accents[accent];

  return (
    <Link href={href} className="group block">
      <div
        className={`relative overflow-hidden rounded-2xl border border-border bg-surface p-6 ring-1 ring-transparent transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_20px_40px_-24px_rgba(0,45,98,0.35)] ${tone.ring}`}
      >
        <div
          className={`flex h-14 w-14 items-center justify-center rounded-xl ${tone.bg}`}
        >
          <Icon className={`h-6 w-6 ${tone.icon}`} strokeWidth={1.75} />
        </div>

        <h2 className="font-display mt-6 text-xl font-semibold text-ink">
          {title}
        </h2>

        <p className="mt-2 text-sm leading-relaxed text-muted">{desc}</p>

        <span className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-ink/60 transition group-hover:text-gold">
          Xem chi tiết
          <ArrowUpRight
            className="h-4 w-4 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
            strokeWidth={1.75}
          />
        </span>
      </div>
    </Link>
  );
}
