"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight,
  CalendarClock,
  FileText,
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

      {error && (
        <p className="mb-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error}
        </p>
      )}

      {!error && !visibleApplications && (
        <p className="text-sm text-[#475569]">Đang tải danh sách hồ sơ...</p>
      )}

      {visibleApplications && visibleApplications.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-[#B6C4D6] bg-[#F8FAFC] px-6 py-14 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-[#B6C4D6] bg-white text-[#64748B]">
            <Inbox className="h-5 w-5" strokeWidth={1.75} />
          </div>
          <p className="text-sm text-[#475569]">
            Không có hồ sơ nào khớp bộ lọc hiện tại.
          </p>
        </div>
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
                      onClick={() => setEditing(app)}
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
    </>
  );
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
