"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Check } from "lucide-react";

import { api, type Checklist } from "../../lib/api";
import RadialProgress from "./RadialProgress";
import HotlineCard from "./HotlineCard";

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

  const topItems = checklist?.items.slice(0, 4) ?? [];

  return (
    <aside className="hidden w-80 shrink-0 flex-col gap-4 overflow-y-auto xl:flex">
      {checklist && (
        <div className="flex items-center gap-4 rounded-2xl border border-border bg-surface p-5">
          <RadialProgress percent={checklist.overall.percent} />
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink">Tiến độ nhận nhà</p>
            <p className="mt-0.5 text-xs text-muted">
              {checklist.overall.completed}/{checklist.overall.total} thủ tục đã hoàn thành
            </p>
          </div>
        </div>
      )}

      {checklist && (
        <div className="rounded-2xl border border-border bg-surface p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-ink">Checklist</p>
            <Link
              href="/checklist"
              className="text-xs font-medium text-gold transition hover:text-gold-soft"
            >
              Xem tất cả
            </Link>
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

      <HotlineCard />
    </aside>
  );
}
