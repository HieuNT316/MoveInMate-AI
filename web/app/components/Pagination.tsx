"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

/** Ngắt trang dùng chung cho các bảng/danh sách bên BQL — dữ liệu đã tải hết
 * về FE (API chưa hỗ trợ phân trang phía server), chỉ cắt hiển thị ở đây. */
export default function Pagination({
  page,
  pageCount,
  onChange,
}: {
  page: number;
  pageCount: number;
  onChange: (page: number) => void;
}) {
  if (pageCount <= 1) return null;

  return (
    <div className="flex items-center justify-between gap-3 border-t border-[#B6C4D6] px-6 py-3">
      <span className="text-xs text-[#64748B]">
        Trang {page} / {pageCount}
      </span>
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          aria-label="Trang trước"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#B6C4D6] text-[#334155] transition hover:border-[#2563EB]/40 hover:text-[#2563EB] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft className="h-4 w-4" strokeWidth={1.75} />
        </button>
        <button
          onClick={() => onChange(page + 1)}
          disabled={page >= pageCount}
          aria-label="Trang sau"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#B6C4D6] text-[#334155] transition hover:border-[#2563EB]/40 hover:text-[#2563EB] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronRight className="h-4 w-4" strokeWidth={1.75} />
        </button>
      </div>
    </div>
  );
}
