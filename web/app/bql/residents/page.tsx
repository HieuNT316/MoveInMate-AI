"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Check,
  Copy,
  FileText,
  KeyRound,
  Loader2,
  Search,
  ShieldOff,
  UserPlus,
  UserRound,
  X,
} from "lucide-react";

import {
  api,
  ApiError,
  describeError,
  type AdminApplication,
  type Dashboard,
  type ResidentDetail,
  type ResidentProgress,
} from "../../../lib/api";
import { useDemoUser } from "../../../lib/useDemoUser";
import CreateResidentDialog from "../../components/CreateResidentDialog";
import Pagination from "../../components/Pagination";

const PAGE_SIZE = 10;

/**
 * "Quản lý cư dân" — tách khỏi /bql/dashboard để dashboard chỉ còn là tổng
 * quan số liệu, còn đây là nơi thao tác trên từng cư dân. Danh sách dùng
 * `GET /admin/dashboard` + `GET /admin/applications`; khoá/mở tài khoản và
 * đặt lại mật khẩu gọi `GET/PATCH /admin/residents/{id}` +
 * `POST /admin/residents/{id}/reset-password` thật (Hiếu, 18/08) — đặt
 * trong modal "Xem" thay vì nút rời trên hàng, vì cần biết đúng trạng thái
 * tài khoản hiện tại mới hiện đúng nhãn nút. "Chỉnh sửa" hồ sơ vẫn khoá
 * "Sắp có" — backend chưa có endpoint cho việc đó (nguyên tắc không vẽ
 * chức năng giả — xem `docs/ROLES_AND_PLAN.md` mục 11).
 */
type StatFilter = "completed" | "not_onboarded";

const FILTER_LABELS: Record<StatFilter, string> = {
  completed: "Đã hoàn tất thủ tục",
  not_onboarded: "Chưa thiết lập hồ sơ",
};

export default function BQLResidentsPage() {
  return (
    <Suspense fallback={null}>
      <BQLResidentsContent />
    </Suspense>
  );
}

// `useSearchParams()` bắt buộc nằm trong <Suspense> — đọc `?filter=` từ các
// thẻ số liệu ở /bql/dashboard, thiếu boundary này thì build fail.
function BQLResidentsContent() {
  const { userId, ready } = useDemoUser();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [applications, setApplications] = useState<AdminApplication[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [viewingId, setViewingId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const statFilterParam = searchParams.get("filter");
  const statFilter: StatFilter | null =
    statFilterParam === "completed" || statFilterParam === "not_onboarded"
      ? statFilterParam
      : null;

  const load = useCallback(async () => {
    try {
      const [dash, apps] = await Promise.all([
        api.getDashboard(userId),
        api.getAdminApplications(userId),
      ]);
      setDashboard(dash);
      setApplications(apps);
      setError(null);
    } catch (err) {
      setError(describeError(err));
    }
  }, [userId]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  const applicationCounts = useMemo(() => {
    const counts = new Map<number, number>();
    for (const app of applications) {
      counts.set(app.user_id, (counts.get(app.user_id) ?? 0) + 1);
    }
    return counts;
  }, [applications]);

  const filtered = useMemo(() => {
    if (!dashboard) return [];
    let residents = dashboard.residents;
    if (statFilter === "completed") {
      residents = residents.filter((r) => r.onboarded && r.bql_scope.percent === 100);
    } else if (statFilter === "not_onboarded") {
      residents = residents.filter((r) => !r.onboarded);
    }
    const q = query.trim().toLowerCase();
    if (!q) return residents;
    return residents.filter(
      (r) => r.full_name.toLowerCase().includes(q) || r.apartment.toLowerCase().includes(q),
    );
  }, [dashboard, query, statFilter]);

  // Đổi bộ lọc/tìm kiếm mà không về trang 1 thì dễ đứng ở trang trống.
  useEffect(() => {
    setPage(1);
  }, [query, statFilter]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const clearStatFilter = () => router.push("/bql/residents");

  return (
    <>
      {statFilter && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-[#2563EB]/30 bg-[#EFF6FF] px-4 py-2.5 text-sm text-[#1D4ED8]">
          Đang lọc theo: <span className="font-medium">{FILTER_LABELS[statFilter]}</span>
          <button
            onClick={clearStatFilter}
            aria-label="Bỏ lọc"
            className="ml-auto flex h-6 w-6 items-center justify-center rounded-full transition hover:bg-white/60"
          >
            <X className="h-3.5 w-3.5" strokeWidth={1.75} />
          </button>
        </div>
      )}

      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="relative w-full max-w-xs">
          <Search
            className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#64748B]"
            strokeWidth={1.75}
          />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm cư dân..."
            className="w-full rounded-xl border border-[#B6C4D6] bg-white py-3 pl-10 pr-3 text-sm text-[#1E293B] shadow-sm placeholder:text-[#64748B] focus:border-[#2563EB] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/15"
          />
        </div>

        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#2563EB] to-[#1D4ED8] px-4 py-3 text-sm font-semibold text-white shadow-[0_10px_22px_-12px_rgba(37,99,235,0.8)] transition-all hover:-translate-y-0.5"
        >
          <UserPlus className="h-4 w-4" strokeWidth={1.75} />
          Tạo tài khoản cư dân
        </button>
      </div>

      {creating && (
        <CreateResidentDialog
          userId={userId}
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            load();
          }}
        />
      )}

      {error && (
        <p className="mb-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error}
        </p>
      )}

      {!error && !dashboard && (
        <p className="text-sm text-[#475569]">Đang tải danh sách cư dân...</p>
      )}

      {dashboard && (
        <div className="overflow-hidden rounded-2xl border border-white/90 bg-white/95 shadow-soft ring-1 ring-[#B6C4D6]/60">
          <div className="flex items-center gap-2 border-b border-[#B6C4D6] px-6 py-4">
            <h3 className="text-sm font-semibold text-[#1E293B]">Danh sách cư dân</h3>
            <span className="text-xs text-[#64748B]">({filtered.length})</span>
          </div>

          {filtered.length === 0 ? (
            <p className="px-6 py-8 text-center text-sm text-[#64748B]">
              Không tìm thấy cư dân khớp &quot;{query}&quot;.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead>
                  <tr className="border-b border-[#B6C4D6] text-[11px] uppercase tracking-wide text-[#64748B]">
                    <th className="px-6 py-3 font-medium">Họ tên</th>
                    <th className="px-3 py-3 font-medium">Căn hộ</th>
                    <th className="px-3 py-3 font-medium">Loại</th>
                    <th className="px-3 py-3 font-medium">Tiến độ</th>
                    <th className="px-3 py-3 font-medium">Số đơn</th>
                    <th className="px-6 py-3 font-medium text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#B6C4D6]">
                  {paginated.map((r) => (
                    <ResidentRow
                      key={r.user_id}
                      resident={r}
                      applicationCount={applicationCounts.get(r.user_id) ?? 0}
                      onView={() => setViewingId(r.user_id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <Pagination page={page} pageCount={pageCount} onChange={setPage} />
        </div>
      )}

      {viewingId !== null && (
        <ResidentDetailModal
          userId={userId}
          targetUserId={viewingId}
          onClose={() => setViewingId(null)}
          onChanged={load}
        />
      )}
    </>
  );
}

function ResidentRow({
  resident,
  applicationCount,
  onView,
}: {
  resident: ResidentProgress;
  applicationCount: number;
  onView: () => void;
}) {
  return (
    <tr className="transition hover:bg-blue-50/45">
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#EFF6FF]">
            <UserRound className="h-4 w-4 text-[#2563EB]" strokeWidth={1.75} />
          </div>
          <div className="min-w-0">
            <p className="truncate font-medium text-[#1E293B]">{resident.full_name}</p>
            {!resident.onboarded && (
              <p className="text-xs text-[#B45309]">Chưa thiết lập hồ sơ</p>
            )}
          </div>
        </div>
      </td>
      <td className="px-3 py-4 text-[#334155]">{resident.apartment}</td>
      <td className="px-3 py-4 text-[#334155]">
        {resident.ownership_type === "owner"
          ? "Chủ hộ"
          : resident.ownership_type === "renter"
            ? "Người thuê"
            : "—"}
      </td>
      <td className="px-3 py-4">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-16 rounded-full bg-[#E2E8F0]">
            <div
              className="h-1.5 rounded-full bg-[#2563EB]"
              style={{ width: `${resident.bql_scope.percent}%` }}
            />
          </div>
          <span className="text-xs font-semibold text-[#334155]">
            {resident.bql_scope.percent}%
          </span>
        </div>
      </td>
      <td className="px-3 py-4 text-[#334155]">{applicationCount}</td>
      <td className="px-6 py-4">
        <div className="flex items-center justify-end gap-1.5">
          <button
            onClick={onView}
            className="rounded-lg bg-[#2563EB] px-3 py-2 text-[11px] font-semibold text-white shadow-sm transition hover:bg-[#1D4ED8]"
          >
            Xem
          </button>
          <Link
            href={`/bql/applications?resident=${resident.user_id}&name=${encodeURIComponent(resident.full_name)}`}
            className="flex items-center gap-1 rounded-lg border border-[#B6C4D6] px-2.5 py-1.5 text-[11px] text-[#334155] transition hover:border-[#2563EB]/40 hover:text-[#2563EB]"
          >
            <FileText className="h-3 w-3" strokeWidth={1.75} />
            Xem đơn
          </Link>
        </div>
      </td>
    </tr>
  );
}

/**
 * Toàn cảnh một cư dân — gọi `GET /admin/residents/{id}` thật (Hiếu, 18/08),
 * kèm khoá/mở tài khoản và đặt lại mật khẩu. Đặt hai hành động này ở đây
 * (không phải nút rời trên hàng bảng) vì cần biết ĐÚNG trạng thái tài khoản
 * hiện tại mới hiện đúng nhãn nút ("Khoá" hay "Mở khoá") — danh sách
 * `/admin/dashboard` không có field này.
 */
function ResidentDetailModal({
  userId,
  targetUserId,
  onClose,
  onChanged,
}: {
  userId: number;
  targetUserId: number;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [detail, setDetail] = useState<ResidentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    try {
      setDetail(await api.getResidentDetail(userId, targetUserId));
      setError(null);
    } catch (err) {
      setError(describeError(err));
    }
  }, [userId, targetUserId]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleStatus = async () => {
    if (!detail || updatingStatus) return;
    const next = detail.account_status === "active" ? "locked" : "active";
    setUpdatingStatus(true);
    try {
      const updated = await api.updateAccountStatus(userId, targetUserId, next);
      setDetail(updated);
      onChanged();
    } catch {
      setError("Không đổi được trạng thái tài khoản, thử lại sau.");
    } finally {
      setUpdatingStatus(false);
    }
  };

  const resetPassword = async () => {
    if (resetting) return;
    setResetting(true);
    setResetError(null);
    try {
      const res = await api.resetResidentPassword(userId, targetUserId);
      setTempPassword(res.temporary_password);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setResetError("Cư dân này chưa được cấp tài khoản đăng nhập.");
      } else {
        setResetError("Không đặt lại được mật khẩu, thử lại sau.");
      }
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F172A]/40 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-[#B6C4D6] bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-lg font-semibold text-[#1E293B]">
            {detail?.profile.full_name ?? "Đang tải..."}
          </h3>
          <button
            onClick={onClose}
            aria-label="Đóng"
            className="flex h-8 w-8 items-center justify-center rounded-full text-[#64748B] transition hover:bg-[#F8FAFC] hover:text-[#1E293B]"
          >
            <X className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>

        {error && (
          <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs text-red-700">
            {error}
          </p>
        )}

        {!error && !detail && (
          <div className="mt-4 flex items-center gap-2 text-sm text-[#64748B]">
            <Loader2 className="h-4 w-4 animate-spin" />
            Đang tải hồ sơ...
          </div>
        )}

        {detail && (
          <>
            <div className="mt-3">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                  detail.account_status === "active"
                    ? "border-emerald/30 bg-emerald/5 text-emerald"
                    : "border-red-200 bg-red-50 text-red-700"
                }`}
              >
                {detail.account_status === "active" ? "Tài khoản đang hoạt động" : "Tài khoản đã bị khoá"}
              </span>
            </div>

            <dl className="mt-4 space-y-3 text-sm">
              <Row label="Email" value={detail.profile.email} />
              <Row label="Toà · Căn hộ" value={`${detail.profile.building} · ${detail.profile.apartment}`} />
              <Row
                label="Loại cư dân"
                value={
                  detail.profile.ownership_type === "owner"
                    ? "Chủ hộ"
                    : detail.profile.ownership_type === "renter"
                      ? "Người thuê"
                      : "Chưa xác định"
                }
              />
              <Row
                label="Onboarding"
                value={detail.profile.onboarding_completed_at ? "Đã hoàn tất" : "Chưa thiết lập"}
              />
              <Row
                label="Checklist BQL"
                value={`${detail.checklist.bql_scope.completed}/${detail.checklist.bql_scope.total} mục (${detail.checklist.bql_scope.percent}%)`}
              />
              <Row label="Hồ sơ đã nộp" value={String(detail.applications.length)} />
            </dl>

            <div className="mt-5 space-y-2 border-t border-[#B6C4D6] pt-4">
              <button
                onClick={toggleStatus}
                disabled={updatingStatus}
                className={`flex w-full items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${
                  detail.account_status === "active"
                    ? "border-red-200 text-red-700 hover:bg-red-50"
                    : "border-emerald/30 text-emerald hover:bg-emerald/5"
                }`}
              >
                {updatingStatus ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ShieldOff className="h-3.5 w-3.5" strokeWidth={1.75} />
                )}
                {detail.account_status === "active" ? "Khoá tài khoản" : "Mở khoá tài khoản"}
              </button>

              {tempPassword ? (
                <div className="rounded-lg border border-[#B6C4D6] bg-[#F8FAFC] px-3 py-2.5 text-xs">
                  <p className="text-[#64748B]">Mật khẩu tạm — chép ngay, sẽ không hiện lại được:</p>
                  <div className="mt-1 flex items-center justify-between gap-2">
                    <code className="font-medium text-[#1E293B]">{tempPassword}</code>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(tempPassword);
                        setCopied(true);
                      }}
                      className="flex shrink-0 items-center gap-1 rounded-md border border-[#B6C4D6] px-2 py-1 text-[11px] text-[#334155] hover:border-[#2563EB]/40"
                    >
                      {copied ? (
                        <Check className="h-3 w-3 text-emerald" strokeWidth={2} />
                      ) : (
                        <Copy className="h-3 w-3" strokeWidth={1.75} />
                      )}
                      {copied ? "Đã chép" : "Chép"}
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={resetPassword}
                  disabled={resetting}
                  className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-[#B6C4D6] px-3 py-2 text-xs font-medium text-[#334155] transition hover:border-[#2563EB]/40 hover:text-[#2563EB] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {resetting ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <KeyRound className="h-3.5 w-3.5" strokeWidth={1.75} />
                  )}
                  Đặt lại mật khẩu
                </button>
              )}
              {resetError && <p className="text-[11px] text-red-600">{resetError}</p>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-[#64748B]">{label}</dt>
      <dd className="font-medium text-[#1E293B]">{value}</dd>
    </div>
  );
}
