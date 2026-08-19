"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  FileText,
  KeyRound,
  Lock,
  Pencil,
  Search,
  ShieldOff,
  UserPlus,
  UserRound,
  X,
} from "lucide-react";

import {
  api,
  describeError,
  type AdminApplication,
  type Dashboard,
  type ResidentProgress,
} from "../../../lib/api";
import { useDemoUser } from "../../../lib/useDemoUser";
import CreateResidentDialog from "../../components/CreateResidentDialog";
import Pagination from "../../components/Pagination";

const PAGE_SIZE = 10;

/**
 * "Quản lý cư dân" — tách khỏi /bql/dashboard để dashboard chỉ còn là tổng
 * quan số liệu, còn đây là nơi thao tác trên từng cư dân. Chỉ dùng lại
 * `GET /admin/dashboard` và `GET /admin/applications` (đã có sẵn) — KHÔNG
 * thêm cột trạng thái tài khoản hay nút khoá/đặt lại mật khẩu có tác dụng
 * thật, vì backend chưa có field/endpoint cho việc đó. Ba nút đó hiện ở
 * dạng khoá "Sắp có" để không ai tưởng nhầm là đã hoạt động — xem
 * `docs/ROLES_AND_PLAN.md` mục 11 (nguyên tắc không vẽ số liệu/chức năng
 * giả).
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
  const [viewing, setViewing] = useState<ResidentProgress | null>(null);
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
            className="w-full rounded-lg border border-[#B6C4D6] bg-white py-2.5 pl-10 pr-3 text-sm text-[#1E293B] placeholder:text-[#64748B] focus:border-[#2563EB] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/15"
          />
        </div>

        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#1D4ED8]"
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
        <div className="overflow-hidden rounded-xl border border-[#B6C4D6] bg-white shadow-sm shadow-slate-200/50">
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
                      onView={() => setViewing(r)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <Pagination page={page} pageCount={pageCount} onChange={setPage} />
        </div>
      )}

      {viewing && <ResidentDetail resident={viewing} onClose={() => setViewing(null)} />}
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
    <tr>
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
            className="rounded-lg border border-[#B6C4D6] px-2.5 py-1.5 text-[11px] text-[#334155] transition hover:border-[#2563EB]/40 hover:text-[#2563EB]"
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
          <div className="mx-1 h-5 w-px shrink-0 bg-[#B6C4D6]" title="Các nút bên phải chưa hoạt động" />
          <LockedAction icon={Pencil} label="Chỉnh sửa" />
          <LockedAction icon={KeyRound} label="Đặt lại đăng nhập" />
          <LockedAction icon={ShieldOff} label="Khoá tài khoản" />
        </div>
      </td>
    </tr>
  );
}

/** Nút chưa có endpoint hậu thuẫn — khoá lại thay vì giả vờ hoạt động. */
function LockedAction({
  icon: Icon,
  label,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  label: string;
}) {
  return (
    <button
      disabled
      title="Sắp có — cần backend bổ sung endpoint, chưa hoạt động"
      className="flex shrink-0 cursor-not-allowed items-center gap-1 rounded-lg border border-dashed border-[#CBD5E1] px-2.5 py-1.5 text-[11px] text-[#94A3B8] opacity-70"
    >
      <Icon className="h-3 w-3" strokeWidth={1.75} />
      {label}
      <Lock className="h-2.5 w-2.5" strokeWidth={2} />
    </button>
  );
}

function ResidentDetail({
  resident,
  onClose,
}: {
  resident: ResidentProgress;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F172A]/40 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-[#B6C4D6] bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-lg font-semibold text-[#1E293B]">
            {resident.full_name}
          </h3>
          <button
            onClick={onClose}
            aria-label="Đóng"
            className="flex h-8 w-8 items-center justify-center rounded-full text-[#64748B] transition hover:bg-[#F8FAFC] hover:text-[#1E293B]"
          >
            <X className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>

        <dl className="mt-4 space-y-3 text-sm">
          <Row label="Căn hộ" value={resident.apartment} />
          <Row
            label="Loại cư dân"
            value={
              resident.ownership_type === "owner"
                ? "Chủ hộ"
                : resident.ownership_type === "renter"
                  ? "Người thuê"
                  : "Chưa xác định"
            }
          />
          <Row label="Onboarding" value={resident.onboarded ? "Đã hoàn tất" : "Chưa thiết lập"} />
          <Row
            label="Checklist BQL"
            value={`${resident.bql_scope.completed}/${resident.bql_scope.total} mục (${resident.bql_scope.percent}%)`}
          />
        </dl>

        <p className="mt-4 text-xs text-[#64748B]">
          Cần xem email/số điện thoại hoặc sửa hồ sơ cư dân? Backend chưa có endpoint cho BQL đọc
          hồ sơ đầy đủ của người khác — đang chờ bổ sung.
        </p>
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
