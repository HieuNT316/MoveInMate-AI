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
import { useToast } from "../components/Toast";
import { api, type Application, type Checklist, type ChecklistItem } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { applicationStatusLabel, applicationStatusTone } from "../../lib/applicationStatus";
import { SELF_DECLARED_DOCUMENT, submitActionLabel } from "../../lib/applicationForms";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import Pagination from "../components/Pagination";

const PAGE_SIZE = 5;

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
  const toast = useToast();

  const [data, setData] = useState<Checklist | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<number | null>(null);
  const [submittingFor, setSubmittingFor] = useState<ChecklistItem | null>(null);
  const [page, setPage] = useState(1);

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
      setError(
        process.env.NODE_ENV === "development"
          ? "Không kết nối được backend. Chạy `uvicorn src.main:app --reload` chưa?"
          : "Không tải được checklist. Kiểm tra kết nối mạng rồi thử lại.",
      );
    }
  }, [userId, router]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  useEffect(() => {
    if (!data || !highlightId) return;
    const itemIndex = data.items.findIndex((item) => item.id === highlightId);
    const targetPage = itemIndex >= 0 ? Math.floor(itemIndex / PAGE_SIZE) + 1 : page;
    if (targetPage !== page) {
      setPage(targetPage);
      return;
    }
    const el = document.getElementById(`checklist-item-${highlightId}`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    setHighlighted(highlightId);
    const timer = setTimeout(() => setHighlighted(null), 2500);
    return () => clearTimeout(timer);
  }, [data, highlightId, page]);

  const toggle = async (itemId: number, completed: boolean) => {
    setPending(itemId);
    try {
      setData(await api.setChecklistItem(userId, itemId, completed));
      toast.show("Đã lưu thay đổi");
    } catch {
      setError("Không cập nhật được trạng thái.");
      toast.show("Cập nhật checklist không thành công", "error");
    } finally {
      setPending(null);
    }
  };

  if (error) {
    return (
      <Layout>
        <ErrorState message={error} onRetry={load} />
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
  if (items.length === 0) return <Layout><EmptyState title="Chưa có việc cần làm" description="Checklist sẽ được tạo theo thông tin căn hộ và nhu cầu bạn đã khai báo." /></Layout>;
  const pageCount = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const paginatedItems = items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

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
        <div className="relative overflow-hidden rounded-2xl border border-white/90 bg-gradient-to-br from-white via-blue-50/30 to-cyan-50/40 p-8 shadow-soft ring-1 ring-border/50">
          <span className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full bg-blue-200/40 blur-3xl" />
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl font-semibold text-ink">
                Tiến độ nhận nhà
              </h2>
              <p className="mt-1 text-sm text-muted">
                {overall.completed}/{overall.total} việc đã hoàn thành
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

          <p className="mt-3 text-sm font-medium text-ink">
            Còn {overall.total - overall.completed} việc cần hoàn thành
          </p>

          <p className="mt-4 border-t border-border pt-4 text-xs text-muted">
            Tiến độ với Ban quản lý — chỉ tính các việc do BQL xử lý:{" "}
            <span className="font-medium text-ink">
              {bql_scope.completed}/{bql_scope.total} ({bql_scope.percent}%)
            </span>
            {overall.total > bql_scope.total && (
              <> · phần còn lại làm tại cơ quan bên ngoài</>
            )}
          </p>
        </div>

        <div className="mt-8 rounded-2xl border border-white/90 bg-surface/95 p-8 shadow-soft ring-1 ring-border/50">
          <h2 className="font-display mb-6 text-xl font-semibold text-ink">
            Các việc trong hành trình nhận nhà
          </h2>

          <div className="space-y-3">
            {paginatedItems.map((item) => {
              const external = item.item_type === "third_party_info";
              // Cập nhật 15/08 (CONTRACT_US13.md mục 2): mọi mục đều nộp
              // được — backend tự gắn kind theo item_type (routes.py), mục
              // "ngoài phạm vi BQL" (tạm trú, cập nhật cư trú) thành hồ sơ
              // self_declared, cư dân chỉ cần nộp ảnh minh chứng.
              const submittable = true;
              const application = applicationByItem.get(item.id);
              return (
                <div
                  key={item.id}
                  id={`checklist-item-${item.id}`}
                  className={`flex gap-4 rounded-2xl border px-5 py-4 transition-colors ${
                    highlighted === item.id
                      ? "animate-[pulse_0.7s_ease-in-out_2] border-gold/50 bg-gold-tint/60"
                      : "border-border bg-surface hover:-translate-y-0.5 hover:border-gold/35 hover:shadow-md"
                  }`}
                >
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
                        className={`text-sm font-medium ${item.completed ? "text-ink" : "text-ink/90"}`}
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
                              {application.status === "rejected"
                                ? "Cần bổ sung hồ sơ"
                                : applicationStatusLabel(application)}
                            </span>
                            {application.bql_note && (
                              <span className="opacity-90">
                                <span className="font-medium">BQL yêu cầu: </span>
                                {application.bql_note}
                              </span>
                            )}

                            <AttachmentUploader
                              userId={userId}
                              applicationId={application.application_id}
                              attachments={application.attachments}
                              required={application.kind === "self_declared"}
                              requiredDocuments={
                                item.item_type === "bql_actionable"
                                  ? item.required_documents
                                  : [SELF_DECLARED_DOCUMENT]
                              }
                              onUploaded={load}
                              onDeleted={load}
                            />
                          </div>
                        ) : (
                          <div>
                            <button
                              onClick={() => setSubmittingFor(item)}
                              className="flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5 text-xs text-ink/90 transition hover:border-gold/50 hover:text-gold"
                            >
                              <FileUp className="h-3.5 w-3.5 text-gold" strokeWidth={1.75} />
                              {submitActionLabel(item.task_name)}
                            </button>
                            {item.completed && (
                              <p className="mt-1.5 text-[11px] text-muted">
                                Tích chỉ là bạn tự xác nhận đã xong — chưa gửi gì cho Ban quản
                                lý. Muốn BQL tiếp nhận/xử lý thì bấm &quot;
                                {submitActionLabel(item.task_name)}&quot; ở trên.
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          <Pagination page={page} pageCount={pageCount} onChange={(nextPage) => { setPage(nextPage); window.scrollTo({ top: 0, behavior: "smooth" }); }} />
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
