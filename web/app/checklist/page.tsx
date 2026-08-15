"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  Building2,
  Check,
  Clock3,
  ExternalLink,
  FileUp,
  Loader2,
  MapPin,
} from "lucide-react";

import Layout from "../components/Layout";
import AttachmentUploader from "../components/AttachmentUploader";
import SubmitApplicationDialog from "../components/SubmitApplicationDialog";
import { api, type Application, type Checklist, type ChecklistItem } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { applicationStatusLabel, applicationStatusTone } from "../../lib/applicationStatus";

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
  const [applications, setApplications] = useState<Application[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<number | null>(null);
  const [submittingFor, setSubmittingFor] = useState<ChecklistItem | null>(null);

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
      // Lỗi tải hồ sơ không được chặn cả trang checklist — cư dân vẫn xem và
      // tick được các mục khác dù danh sách hồ sơ đã nộp tải hỏng.
      try {
        setApplications(await api.getApplications(userId));
      } catch (err) {
        console.error("[checklist] không tải được danh sách hồ sơ đã nộp:", err);
      }
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

  // Mỗi mục chỉ có MỘT hồ sơ đang mở — `applications` trả mới nhất trước nên
  // giữ bản ghi đầu tiên gặp cho mỗi `checklist_item_id` là đủ, không cần lọc
  // theo trạng thái "đang mở" ở FE (backend đã tự chặn nộp trùng bằng 409).
  const applicationByItem = new Map<number, Application>();
  for (const app of applications) {
    if (!applicationByItem.has(app.checklist_item_id)) {
      applicationByItem.set(app.checklist_item_id, app);
    }
  }

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
              // Cập nhật 15/08 (CONTRACT_US13.md mục 2): mọi mục đều nộp
              // được — backend tự gắn kind theo item_type (routes.py), mục
              // "ngoài phạm vi BQL" (tạm trú, cập nhật cư trú) thành hồ sơ
              // self_declared, cư dân chỉ cần nộp ảnh minh chứng.
              const submittable = true;
              const application = applicationByItem.get(item.id);
              return (
                <li
                  key={item.id}
                  id={`checklist-item-${item.id}`}
                  className={`relative flex gap-4 rounded-xl pb-7 transition-colors last:pb-0 ${
                    highlighted === item.id
                      ? "animate-[pulse_0.7s_ease-in-out_2] bg-gold-tint/60 ring-1 ring-gold/40"
                      : ""
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

                    {/* US-13: 3 trường chỉ có ở mục `bql_actionable` — mục
                        third_party_info không có bộ phận nào của BQL phụ
                        trách nên backend luôn trả null cho cả ba. */}
                    {item.handling_department && (
                      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
                        <span className="flex items-center gap-1.5">
                          <Building2 className="h-3.5 w-3.5 text-gold" strokeWidth={1.75} />
                          {item.handling_department}
                        </span>
                        {item.submission_location && (
                          <span className="flex items-center gap-1.5">
                            <MapPin className="h-3.5 w-3.5 text-gold" strokeWidth={1.75} />
                            {item.submission_location}
                          </span>
                        )}
                        {item.processing_time && (
                          <span className="flex items-center gap-1.5">
                            <Clock3 className="h-3.5 w-3.5 text-gold" strokeWidth={1.75} />
                            {item.processing_time}
                          </span>
                        )}
                      </div>
                    )}

                    {submittable && (
                      <div className="mt-3">
                        {application ? (
                          <div
                            className={`flex flex-col gap-1 rounded-xl border px-3.5 py-2.5 text-xs ${applicationStatusTone(application.status)}`}
                          >
                            <span className="flex items-center gap-1.5 font-medium">
                              {(application.status === "needs_info" ||
                                application.status === "rejected") && (
                                <AlertCircle className="h-3.5 w-3.5" strokeWidth={1.75} />
                              )}
                              {applicationStatusLabel(application)}
                            </span>
                            {application.bql_note &&
                              (application.status === "needs_info" ||
                                application.status === "rejected") && (
                                <span className="opacity-90">{application.bql_note}</span>
                              )}

                            <AttachmentUploader
                              userId={userId}
                              applicationId={application.application_id}
                              attachments={application.attachments}
                              required={application.kind === "self_declared"}
                              onUploaded={load}
                            />
                          </div>
                        ) : (
                          <button
                            onClick={() => setSubmittingFor(item)}
                            className="flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5 text-xs text-ink/80 transition hover:border-gold/50 hover:text-gold"
                          >
                            <FileUp className="h-3.5 w-3.5 text-gold" strokeWidth={1.75} />
                            Nộp hồ sơ
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </div>

      {submittingFor && (
        <SubmitApplicationDialog
          userId={userId}
          item={submittingFor}
          onClose={() => setSubmittingFor(null)}
          onSubmitted={() => {
            setSubmittingFor(null);
            load();
          }}
        />
      )}
    </Layout>
  );
}
