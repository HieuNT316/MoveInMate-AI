"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FileText, Inbox, Paperclip, Pencil, X } from "lucide-react";

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
    if (!applications || !residentId) return applications;
    const id = Number(residentId);
    return applications.filter((a) => a.user_id === id);
  }, [applications, residentId]);

  const clearResidentFilter = () => router.push("/bql/applications");

  // Đổi bộ lọc mà không về trang 1 thì dễ đứng ở trang trống.
  useEffect(() => {
    setPage(1);
  }, [statusFilter, department, residentId]);

  const pageCount = Math.max(1, Math.ceil((visibleApplications?.length ?? 0) / PAGE_SIZE));
  const paginatedApplications = (visibleApplications ?? []).slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  return (
    <>
      {residentId && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-[#2563EB]/30 bg-[#EFF6FF] px-4 py-2.5 text-sm text-[#1D4ED8]">
          Đang lọc theo cư dân: <span className="font-medium">{residentName ?? `#${residentId}`}</span>
          <button
            onClick={clearResidentFilter}
            aria-label="Bỏ lọc theo cư dân"
            className="ml-auto flex h-6 w-6 items-center justify-center rounded-full transition hover:bg-white/60"
          >
            <X className="h-3.5 w-3.5" strokeWidth={1.75} />
          </button>
        </div>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-3">
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
        <div className="overflow-hidden rounded-xl border border-[#B6C4D6] bg-white shadow-sm shadow-slate-200/50">
          <div className="divide-y divide-[#B6C4D6]">
            {paginatedApplications.map((app) => (
              <div key={app.application_id} className="flex items-start gap-4 px-6 py-4">
                <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#EFF6FF] text-[#2563EB]">
                  <FileText className="h-4 w-4" strokeWidth={1.75} />
                </div>

                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[#1E293B]">
                    {app.task_name}
                    <span className="ml-1.5 font-normal text-[#64748B]">
                      — {app.full_name} · {app.apartment}
                    </span>
                  </p>
                  <p className="mt-0.5 text-xs text-[#64748B]">
                    {app.handling_department ?? "—"}
                    {app.kind === "self_declared" && <> · tự khai, cần ảnh minh chứng</>}
                  </p>
                  {app.note && (
                    <p className="mt-1.5 text-xs text-[#475569]">Ghi chú cư dân: {app.note}</p>
                  )}
                  {app.attachments.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap items-center gap-2">
                      {app.attachments.map((att) => (
                        <a
                          key={att.attachment_id}
                          href={att.url ?? undefined}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 rounded-full border border-[#B6C4D6] bg-[#F8FAFC] px-2 py-0.5 text-[11px] text-[#334155] hover:border-[#2563EB]/40 hover:text-[#2563EB]"
                        >
                          <Paperclip className="h-3 w-3" strokeWidth={1.75} />
                          {att.filename}
                        </a>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex shrink-0 flex-col items-end gap-2">
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${applicationStatusTone(app.status)}`}
                  >
                    {applicationStatusLabel(app)}
                  </span>
                  <button
                    onClick={() => setEditing(app)}
                    className="flex items-center gap-1.5 rounded-lg border border-[#B6C4D6] px-2.5 py-1.5 text-[11px] text-[#334155] transition hover:border-[#2563EB]/40 hover:text-[#2563EB]"
                  >
                    <Pencil className="h-3 w-3" strokeWidth={1.75} />
                    Cập nhật
                  </button>
                </div>
              </div>
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
