"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Check, ExternalLink, Loader2 } from "lucide-react";

import Layout from "../components/Layout";
import { api, type Checklist } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";

export default function ChecklistPage() {
  return (
    <Suspense fallback={null}>
      <ChecklistContent />
    </Suspense>
  );
}

// `useSearchParams()` bắt buộc nằm trong <Suspense> (đọc `?item=` từ nút
// "Đến mục này" trong chat) — thiếu boundary này thì `next build` fail.
function ChecklistContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { userId, ready } = useDemoUser();

  const [data, setData] = useState<Checklist | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<number | null>(null);

  // Đích tới từ nút "Đến mục này" trong chat (SuggestedAction) — cuộn và
  // đánh dấu đúng mục một lần sau khi checklist tải xong.
  const highlightId = Number(searchParams.get("item")) || null;
  const [highlighted, setHighlighted] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const checklist = await api.getChecklist(userId);
      if (!checklist.onboarding_completed) {
        router.push("/onboarding");
        return;
      }
      setData(checklist);
      setError(null);
    } catch {
      setError("Không kết nối được backend. Chạy `uvicorn src.main:app --reload` chưa?");
    }
  }, [userId, router]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  useEffect(() => {
    if (!data || !highlightId) return;
    const el = document.getElementById(`checklist-item-${highlightId}`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    setHighlighted(highlightId);
    const timer = setTimeout(() => setHighlighted(null), 2500);
    return () => clearTimeout(timer);
  }, [data, highlightId]);

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

        <div className="mt-8 rounded-2xl border border-border bg-surface p-8">
          <h2 className="font-display mb-6 text-xl font-semibold text-ink">
            Thủ tục cần hoàn thành
          </h2>

          <ol className="space-y-0">
            {items.map((item, index) => {
              const external = item.item_type === "third_party_info";
              return (
                <li
                  key={item.id}
                  id={`checklist-item-${item.id}`}
                  className={`relative flex gap-4 rounded-xl pb-7 transition-colors last:pb-0 ${
                    highlighted === item.id ? "bg-gold-tint/60 ring-1 ring-gold/40" : ""
                  }`}
                >
                  {index !== items.length - 1 && (
                    <span
                      className={`absolute left-[11px] top-7 h-[calc(100%-1.75rem)] w-px ${
                        item.completed ? "bg-emerald/40" : "bg-border"
                      }`}
                    />
                  )}

                  <button
                    onClick={() => toggle(item.id, !item.completed)}
                    disabled={pending === item.id}
                    aria-label={item.task_name}
                    className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition ${
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

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`text-sm font-medium ${item.completed ? "text-ink" : "text-ink/80"}`}
                      >
                        {item.task_name}
                      </span>
                      <span className="rounded-full bg-background px-2 py-0.5 text-[11px] text-muted">
                        {item.category}
                      </span>
                      {external && (
                        <span className="flex items-center gap-1 rounded-full border border-gold/40 bg-gold-tint px-2 py-0.5 text-[11px] text-gold">
                          <ExternalLink className="h-2.5 w-2.5" strokeWidth={2} />
                          Ngoài phạm vi BQL
                        </span>
                      )}
                    </div>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted">
                      {item.description}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </Layout>
  );
}
