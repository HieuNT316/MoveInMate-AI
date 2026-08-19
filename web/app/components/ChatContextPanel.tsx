"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Check, PhoneCall } from "lucide-react";

import { api, type Checklist } from "../../lib/api";
import { HOTLINE } from "./HotlineCard";

export default function ChatContextPanel({
  userId,
  ready,
}: {
  userId: number;
  ready: boolean;
}) {
  const [checklist, setChecklist] = useState<Checklist | null>(null);

  useEffect(() => {
    if (!ready) return;
    // Widget phụ — hỏng thì ẩn đi, không được kéo cả trang chat theo, giống
    // cách `loadHistory` trong chat/page.tsx xử lý lỗi tải phụ.
    api
      .getChecklist(userId)
      .then(setChecklist)
      .catch(() => setChecklist(null));
  }, [ready, userId]);

  const topItems = checklist?.items.slice(0, 5) ?? [];

  return (
    <aside className="hidden w-64 shrink-0 flex-col gap-3 overflow-y-auto xl:flex">
      {checklist && (
        <div className="rounded-2xl border border-white/90 bg-surface/95 p-5 shadow-soft ring-1 ring-border/50">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink">Việc của bạn</p>
            <Link
              href="/checklist"
              className="text-xs font-medium text-gold transition hover:text-gold-soft"
            >
              Xem tất cả
            </Link>
          </div>
          <div className="mt-4 flex items-end justify-between">
            <p className="text-2xl font-bold text-ink">{checklist.overall.percent}%</p>
            <p className="text-xs text-muted">{checklist.overall.completed}/{checklist.overall.total} việc</p>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-border/70">
            <div className="h-full rounded-full bg-gradient-to-r from-gold to-cyan-500" style={{ width: `${checklist.overall.percent}%` }} />
          </div>
          <ul className="mt-3 space-y-2.5">
            {topItems.map((item) => (
              <li key={item.id} className="flex items-start gap-2.5">
                <span
                  className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                    item.completed
                      ? "border-emerald bg-emerald text-white"
                      : "border-border text-transparent"
                  }`}
                >
                  <Check className="h-2.5 w-2.5" strokeWidth={3} />
                </span>
                <span
                  className={`text-xs leading-snug ${
                    item.completed ? "text-muted line-through" : "text-ink/90"
                  }`}
                >
                  {item.task_name}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-2xl border border-blue-200 bg-blue-50/80 p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-ink">Cần hỗ trợ?</p>
        <a href={`tel:${HOTLINE.number.replace(/\s/g, "")}`} className="mt-2 flex items-center gap-2 text-sm font-semibold text-gold">
          <PhoneCall className="h-4 w-4" />
          {HOTLINE.number}
        </a>
        <p className="mt-1 text-[10px] leading-relaxed text-muted">Nhấn phím 4 · hỗ trợ 24/7</p>
      </div>
    </aside>
  );
}
