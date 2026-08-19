"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight,
  CalendarClock,
  FileText,
  Eye,
  Inbox,
  Paperclip,
  Pencil,
  Search,
  X,
} from "lucide-react";

import {
  api,
  describeError,
  type AdminApplication,
  type ApplicationStatus,
} from "../../../lib/api";
import { useDemoUser } from "../../../lib/useDemoUser";
import { applicationStatusLabel, applicationStatusTone } from "../../../lib/applicationStatus";
import UpdateApplicationStatusDialog from "../../components/UpdateApplicationStatusDialog";
import Pagination from "../../components/Pagination";
import EmptyState from "../../components/EmptyState";
import ErrorState from "../../components/ErrorState";
import AttachmentPreviewModal from "../../components/AttachmentPreviewModal";

const PAGE_SIZE = 10;

const STATUS_PROGRESS: Record<ApplicationStatus, number> = {
  received: 25,
  processing: 55,
  needs_info: 45,
  approved: 85,
  delivered: 100,
  rejected: 100,
};

const STATUS_FILTERS: { value: ApplicationStatus | "all"; label: string }[] = [
  { value: "all", label: "Tất cả trạng thái" },
  { value: "received", label: "Đã tiếp nhận" },
  { value: "processing", label: "Đang xử lý" },
  { value: "needs_info", label: "Cần bổ sung" },
  { value: "approved", label: "Đã duyệt" },
  { value: "delivered", label: "Đã trả kết quả" },
  { value: "rejected", label: "Từ chối" },
];

export default function BQLApplicationsPage() {
  return (
    <Suspense fallback={null}>
      <BQLApplicationsContent />
    </Suspense>
  );
}

// `useSearchParams()` bắt buộc nằm trong <Suspense> — đọc `?resident=` từ
// link "Xem đơn" ở trang Quản lý cư dân, thiếu boundary này thì build fail.
function BQLApplicationsContent() {
  const { userId, ready } = useDemoUser();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [applications, setApplications] = useState<AdminApplication[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "all">("all");
  const [department, setDepartment] = useState("");
  const [editing, setEditing] = useState<AdminApplication | null>(null);
  const [viewing, setViewing] = useState<AdminApplication | null>(null);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");

  const residentId = searchParams.get("resident");
  const residentName = searchParams.get("name");

  const load = useCallback(async () => {
    try {
      const apps = await api.getAdminApplications(userId, {
        status: statusFilter === "all" ? undefined : statusFilter,
        department: department.trim() || undefined,
      });
      setApplications(apps);
      setError(null);
    } catch (err) {
      setError(describeError(err));
    }
  }, [userId, statusFilter, department]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  const departments = Array.from(
    new Set((applications ?? []).map((a) => a.handling_department).filter(Boolean)),
  ) as string[];

  // Lọc theo cư dân ngay ở FE — `GET /admin/applications` chưa hỗ trợ filter
  // theo user_id, nhưng dữ liệu đã có sẵn trong response chung nên không cần
  // endpoint mới cho việc này.
  const visibleApplications = useMemo(() => {
    if (!applications) return applications;
    const normalizedQuery = query.trim().toLocaleLowerCase("vi");
    const id = residentId ? Number(residentId) : null;
    return applications.filter((app) => {
      if (id !== null && app.user_id !== id) return false;
      if (!normalizedQuery) return true;
      return [app.full_name, app.apartment, app.task_name, app.handling_department ?? ""]
        .some((value) => value.toLocaleLowerCase("vi").includes(normalizedQuery));
    });
  }, [applications, query, residentId]);

  const clearResidentFilter = () => router.push("/bql/applications");

  // Đổi bộ lọc mà không về trang 1 thì dễ đứng ở trang trống.
  useEffect(() => {
    setPage(1);
  }, [statusFilter, department, residentId, query]);

  const pageCount = Math.max(1, Math.ceil((visibleApplications?.length ?? 0) / PAGE_SIZE));
  const paginatedApplications = (visibleApplications ?? []).slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  return (
    <>
      <label className="mb-4 flex h-12 items-center gap-3 rounded-xl border border-[#B6C4D6] bg-white px-4 shadow-sm shadow-slate-200/30 focus-within:border-[#2563EB] focus-within:ring-2 focus-within:ring-[#2563EB]/10">
        <Search className="h-4 w-4 shrink-0 text-[#64748B]" strokeWidth={1.75} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Tìm cư dân, mã căn, tên thủ tục hoặc bộ phận..."
          className="min-w-0 flex-1 bg-transparent text-sm text-[#1E293B] outline-none placeholder:text-[#94A3B8]"
        />
        {query && (
          <button onClick={() => setQuery("")} aria-label="Xóa tìm kiếm" className="text-[#64748B] hover:text-[#1E293B]">
            <X className="h-4 w-4" />
          </button>
        )}
      </label>

      <div className="mb-6 rounded-xl border border-[#B6C4D6] bg-white p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#475569]">Bộ lọc</p>
          <p className="text-sm font-semibold text-[#1E293B]">{visibleApplications?.length ?? 0} hồ sơ</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {residentId && (
            <button
              onClick={clearResidentFilter}
              className="flex items-center gap-2 rounded-lg border border-[#2563EB]/30 bg-[#EFF6FF] px-3.5 py-2.5 text-sm text-[#1D4ED8]"
            >
              Cư dân: <span className="font-medium">{residentName ?? `#${residentId}`}</span>
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value as ApplicationStatus | "all")}
          className="rounded-lg border border-[#B6C4D6] bg-white px-3.5 py-2.5 text-sm text-[#1E293B] focus:border-[#2563EB] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/15"
        >
          {STATUS_FILTERS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <select
          value={department}
          onChange={(event) => setDepartment(event.target.value)}
          className="rounded-lg border border-[#B6C4D6] bg-white px-3.5 py-2.5 text-sm text-[#1E293B] focus:border-[#2563EB] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/15"
        >
          <option value="">Tất cả bộ phận</option>
          {departments.map((dep) => (
            <option key={dep} value={dep}>
              {dep}
            </option>
          ))}
        </select>
        </div>
      </div>

      {error && <div className="mb-6"><ErrorState message={error} onRetry={load} /></div>}

      {!error && !visibleApplications && (
        <p className="text-sm text-[#475569]">Đang tải danh sách hồ sơ...</p>
      )}

      {visibleApplications && visibleApplications.length === 0 && (
        <EmptyState icon={Inbox} title={applications?.length === 0 ? "Chưa có yêu cầu nào" : "Không có kết quả"} description={applications?.length === 0 ? "Khi cư dân nộp hồ sơ, yêu cầu sẽ xuất hiện tại đây để Ban quản lý tiếp nhận." : "Thử thay đổi từ khóa hoặc bộ lọc hiện tại."} />
      )}

      {visibleApplications && visibleApplications.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-soft ring-1 ring-[#B6C4D6]/60">
          <div className="divide-y divide-[#D9E2EC]">
            {paginatedApplications.map((app) => (
              <article key={app.application_id} className="transition px-5 py-5 hover:bg-blue-50/35 sm:px-6">
                <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#EFF6FF] text-[#2563EB]">
                  <FileText className="h-4 w-4" strokeWidth={1.75} />
                </div>

                <div className="min-w-0 flex-1">
                  <h2 className="text-base font-semibold text-[#1E293B]">{app.task_name}</h2>
                  <p className="mt-0.5 text-sm text-[#475569]">{app.full_name} · Căn {app.apartment}</p>
                </div>
                  <span
                    className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-medium ${applicationStatusTone(app.status)}`}
                  >
                    {applicationStatusLabel(app)}
                  </span>
                </div>

                <div className="mt-4 grid gap-4 pl-0 sm:grid-cols-[1fr_auto] sm:pl-14">
                  <div>
                    <div className="flex items-center justify-between text-xs text-[#64748B]">
                      <span>Tiến độ xử lý</span>
                      <span className="font-semibold text-[#334155]">{STATUS_PROGRESS[app.status]}%</span>
                    </div>
                    <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-[#E2E8F0]">
                      <div className="h-full rounded-full bg-gradient-to-r from-[#2563EB] to-[#22C1DC]" style={{ width: `${STATUS_PROGRESS[app.status]}%` }} />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-[#64748B]">
                      <span className="flex items-center gap-1.5"><Paperclip className="h-3.5 w-3.5" />{app.attachments.length} tài liệu</span>
                      <span className="flex items-center gap-1.5"><CalendarClock className="h-3.5 w-3.5" />Cập nhật {formatDateTime(app.updated_at)}</span>
                      {app.handling_department && <span>{app.handling_department}</span>}
                    </div>
                  </div>
                  <div className="flex items-end gap-2">
                    <button
                      onClick={() => setViewing(app)}
                      className="flex items-center gap-1.5 rounded-lg bg-[#2563EB] px-3.5 py-2 text-xs font-medium text-white transition hover:bg-[#1D4ED8]"
                    >
                      Xem hồ sơ <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => setEditing(app)}
                      className="flex items-center gap-1.5 rounded-lg border border-[#B6C4D6] px-3.5 py-2 text-xs font-medium text-[#334155] transition hover:border-[#2563EB]/40 hover:text-[#2563EB]"
                    >
                      <Pencil className="h-3.5 w-3.5" /> Cập nhật
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
          <Pagination page={page} pageCount={pageCount} onChange={setPage} />
        </div>
      )}

      {editing && (
        <UpdateApplicationStatusDialog
          userId={userId}
          application={editing}
          onClose={() => setEditing(null)}
          onUpdated={() => {
            setEditing(null);
            load();
          }}
        />
      )}

      {viewing && (
        <ApplicationDetailDialog
          userId={userId}
          application={viewing}
          onClose={() => setViewing(null)}
          onEdit={() => {
            setEditing(viewing);
            setViewing(null);
          }}
        />
      )}
    </>
  );
}

function ApplicationDetailDialog({
  userId,
  application,
  onClose,
  onEdit,
}: {
  userId: number;
  application: AdminApplication;
  onClose: () => void;
  onEdit: () => void;
}) {
  const [previewing, setPreviewing] = useState<(typeof application.attachments)[number] | null>(null);
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previous; };
  }, []);

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center overscroll-none bg-[#0F172A]/45 p-4" role="dialog" aria-modal="true" aria-label="Chi tiết hồ sơ">
      <div className="max-h-[calc(100dvh-2rem)] w-full max-w-xl overflow-y-auto overscroll-contain rounded-2xl border border-[#B6C4D6] bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-blue-600">Chi tiết yêu cầu</p>
            <h3 className="mt-1 text-lg font-semibold text-slate-800">{application.task_name}</h3>
            <p className="mt-1 text-sm text-slate-500">{application.full_name} · Căn {application.apartment}</p>
          </div>
          <button onClick={onClose} aria-label="Đóng" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100"><X className="h-4 w-4" /></button>
        </div>

        <dl className="mt-6 grid gap-4 rounded-xl bg-slate-50 p-4 sm:grid-cols-2">
          <Detail label="Trạng thái" value={applicationStatusLabel(application)} />
          <Detail label="Bộ phận xử lý" value={application.handling_department ?? "Chưa phân công"} />
          <Detail label="Ngày gửi" value={formatDateTime(application.created_at)} />
          <Detail label="Cập nhật gần nhất" value={formatDateTime(application.updated_at)} />
          <Detail label="Tài liệu đính kèm" value={`${application.attachments.length} tệp`} />
          <Detail label="Địa điểm nộp" value={application.submission_location ?? "Nộp trực tuyến"} />
        </dl>

        <section className="mt-4 rounded-xl border border-slate-200 p-4">
          <div className="flex items-center justify-between gap-3">
            <h4 className="text-sm font-semibold text-slate-800">Giấy tờ cư dân đã nộp</h4>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">{application.attachments.length} tệp</span>
          </div>
          {application.attachments.length === 0 ? (
            <div className="mt-3 rounded-lg border border-dashed border-amber-300 bg-amber-50 px-4 py-4 text-sm text-amber-800">
              Cư dân chưa tải giấy tờ nào cho yêu cầu này. Chưa nên duyệt hồ sơ cho đến khi có đủ minh chứng.
            </div>
          ) : (
            <ul className="mt-3 space-y-2">
              {application.attachments.map((attachment) => (
                <li key={attachment.attachment_id} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
                  <FileText className="h-4 w-4 shrink-0 text-blue-600" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800">{attachment.filename}</p>
                    <p className="mt-0.5 text-[11px] text-slate-500">{attachment.document_type ?? "Chưa phân loại"} · {formatFileSize(attachment.size_bytes)}</p>
                  </div>
                  <button type="button" onClick={() => setPreviewing(attachment)} className="flex shrink-0 items-center gap-1.5 rounded-lg border border-blue-200 bg-white px-3 py-2 text-xs font-medium text-blue-700 hover:bg-blue-50">
                    <Eye className="h-3.5 w-3.5" />Xem giấy tờ
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {(application.note || application.bql_note) && (
          <div className="mt-4 space-y-3">
            {application.note && <Note label="Ghi chú của cư dân" value={application.note} />}
            {application.bql_note && <Note label="Phản hồi của Ban quản lý" value={application.bql_note} />}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">Đóng</button>
          <button onClick={onEdit} className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700"><Pencil className="h-4 w-4" />Cập nhật trạng thái</button>
        </div>
        {previewing && <AttachmentPreviewModal userId={userId} applicationId={application.application_id} attachment={previewing} onClose={() => setPreviewing(null)} />}
      </div>
    </div>,
    document.body,
  );
}

function formatFileSize(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 text-sm font-medium text-slate-800">{value}</dd></div>;
}

function Note({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-200 px-4 py-3"><p className="text-xs font-medium text-slate-500">{label}</p><p className="mt-1 text-sm leading-6 text-slate-700">{value}</p></div>;
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
