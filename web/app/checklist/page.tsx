"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Check,
  ChevronDown,
  ExternalLink,
  Loader2,
} from "lucide-react";

import Layout from "../components/Layout";
import {
  api,
  describeError,
  type Checklist,
  type ChecklistItem,
} from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";

const CATEGORY_DOTS = [
  "bg-gold",
  "bg-emerald",
  "bg-amber-500",
  "bg-purple-500",
  "bg-rose-500",
  "bg-cyan-600",
];

function categoryDot(category: string, order: string[]): string {
  const index = order.indexOf(category);
  return CATEGORY_DOTS[index % CATEGORY_DOTS.length];
}

type Filter = "all" | "pending" | "done";

export default function ChecklistPage() {
  const router = useRouter();
  const { userId, ready } = useDemoUser();

  const [data, setData] = useState<Checklist | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<number | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const checklist = await api.getChecklist(userId);
      if (!checklist.onboarding_completed) {
        router.push("/onboarding");
        return;
      }
      setData(checklist);
      setError(null);
    } catch (err) {
      setError(describeError(err));
    }
  }, [userId, router]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  const toggle = async (itemId: number, completed: boolean) => {
    setPending(itemId);
    try {
      setData(await api.setChecklistItem(userId, itemId, completed));
    } catch {
      setError("Không cập nhật được trạng thái.");
    } finally {
      setPending(null);
    }
  };

  if (error) {
    return (
      <Layout>
        <p className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error}
        </p>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout>
        <div className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Đang tải checklist...
        </div>
      </Layout>
    );
  }

  const { items, overall, bql_scope } = data;

  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        <div className="rounded-2xl border border-border bg-surface p-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl font-semibold text-ink">
                Tiến độ nhận nhà
              </h2>
              <p className="mt-1 text-sm text-muted">
                {overall.completed}/{overall.total} thủ tục đã hoàn thành
              </p>
            </div>
            <span className="font-display text-3xl font-semibold text-emerald">
              {overall.percent}%
            </span>
          </div>

          <div className="mt-5 h-3 w-full rounded-full bg-border">
            <div
              className="h-3 rounded-full bg-gradient-to-r from-gold to-gold-soft transition-all"
              style={{ width: `${overall.percent}%` }}
            />
          </div>

          <p className="mt-4 border-t border-border pt-4 text-xs text-muted">
            Trong đó thủ tục do Ban quản lý xử lý:{" "}
            <span className="font-medium text-ink">
              {bql_scope.completed}/{bql_scope.total} ({bql_scope.percent}%)
            </span>
            {overall.total > bql_scope.total && (
              <> · phần còn lại làm tại cơ quan bên ngoài</>
            )}
          </p>
        </div>

        <div className="mt-8 flex flex-wrap gap-2">
          {(
            [
              { id: "all", label: "Tất cả", count: items.length },
              {
                id: "pending",
                label: "Cần làm",
                count: items.filter((i) => !i.completed).length,
              },
              {
                id: "done",
                label: "Hoàn tất",
                count: items.filter((i) => i.completed).length,
              },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id)}
              className={`flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-medium transition ${
                filter === tab.id
                  ? "border-ink bg-ink text-white"
                  : "border-border bg-surface text-muted hover:border-gold/40 hover:text-ink"
              }`}
            >
              {tab.label}
              <span
                className={`rounded-full px-1.5 text-[11px] ${
                  filter === tab.id ? "bg-white/20" : "bg-background"
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        <ChecklistGroups
          items={items}
          filter={filter}
          expandedId={expandedId}
          setExpandedId={setExpandedId}
          pending={pending}
          onToggle={toggle}
        />
      </div>
    </Layout>
  );
}

function ChecklistGroups({
  items,
  filter,
  expandedId,
  setExpandedId,
  pending,
  onToggle,
}: {
  items: ChecklistItem[];
  filter: Filter;
  expandedId: number | null;
  setExpandedId: (id: number | null) => void;
  pending: number | null;
  onToggle: (itemId: number, completed: boolean) => void;
}) {
  const categoryOrder = Array.from(new Set(items.map((i) => i.category)));

  const filtered = items.filter((item) => {
    if (filter === "pending") return !item.completed;
    if (filter === "done") return item.completed;
    return true;
  });

  return (
    <div className="mt-6 space-y-6">
      {categoryOrder.map((category) => {
        const group = filtered.filter((i) => i.category === category);
        if (group.length === 0) return null;

        return (
          <div key={category}>
            <div className="mb-2.5 flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${categoryDot(category, categoryOrder)}`}
              />
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
                {category}
              </p>
            </div>

            <div className="space-y-2">
              {group.map((item) => {
                const external = item.item_type === "third_party_info";
                const isExpanded = expandedId === item.id;

                return (
                  <div
                    key={item.id}
                    className="overflow-hidden rounded-xl border border-border bg-surface"
                  >
                    <div className="flex items-center gap-3 px-4 py-3.5">
                      <button
                        onClick={() => onToggle(item.id, !item.completed)}
                        disabled={pending === item.id}
                        aria-label={item.task_name}
                        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition ${
                          item.completed
                            ? "border-emerald bg-emerald text-white"
                            : "border-border text-transparent hover:border-gold/50"
                        }`}
                      >
                        {pending === item.id ? (
                          <Loader2 className="h-3 w-3 animate-spin text-muted" />
                        ) : (
                          <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                        )}
                      </button>

                      <button
                        onClick={() =>
                          setExpandedId(isExpanded ? null : item.id)
                        }
                        className="flex min-w-0 flex-1 items-center gap-2 text-left"
                      >
                        <span
                          className={`truncate text-sm font-medium ${
                            item.completed
                              ? "text-muted line-through"
                              : "text-ink"
                          }`}
                        >
                          {item.task_name}
                        </span>
                        {external && (
                          <span className="flex shrink-0 items-center gap-1 rounded-full border border-gold/40 bg-gold-tint px-2 py-0.5 text-[11px] text-gold">
                            <ExternalLink
                              className="h-2.5 w-2.5"
                              strokeWidth={2}
                            />
                            Ngoài BQL
                          </span>
                        )}
                        <ChevronDown
                          className={`ml-auto h-3.5 w-3.5 shrink-0 text-muted transition-transform ${
                            isExpanded ? "rotate-180" : ""
                          }`}
                          strokeWidth={2}
                        />
                      </button>
                    </div>

                    {isExpanded && (
                      <div className="border-t border-border px-4 py-3.5 pl-[52px]">
                        <p className="text-sm leading-relaxed text-muted">
                          {item.description}
                        </p>
                        {item.completed_at && (
                          <p className="mt-2 text-xs text-muted">
                            Hoàn tất lúc: {item.completed_at}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
