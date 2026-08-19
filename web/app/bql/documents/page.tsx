"use client";

import { useMemo, useState } from "react";
import {
  BookOpen,
  Building2,
  FileCheck2,
  FileText,
  Scale,
  Search,
  ShieldCheck,
} from "lucide-react";
import Pagination from "../../components/Pagination";

const PAGE_SIZE = 4;

const DOCUMENTS = [
  { title: "Quy trình nhận nhà", group: "Quy trình BQL", version: "Cập nhật 18/08/2026", icon: Building2, tone: "blue" },
  { title: "Cấp thẻ cư dân và đăng ký tiện ích", group: "Quy trình BQL", version: "Cập nhật 18/08/2026", icon: FileCheck2, tone: "cyan" },
  { title: "Cập nhật thông tin cư trú", group: "Quy trình BQL", version: "Cập nhật 18/08/2026", icon: ShieldCheck, tone: "emerald" },
  { title: "Cơ cấu và quy trình phối hợp", group: "Vận hành nội bộ", version: "Cập nhật 18/08/2026", icon: BookOpen, tone: "violet" },
  { title: "Quy chế quản lý, sử dụng nhà chung cư", group: "Văn bản pháp lý", version: "Thông tư 05/2024/TT-BXD", icon: Scale, tone: "amber" },
] as const;

const TONE = {
  blue: "bg-blue-50 text-blue-600",
  cyan: "bg-cyan-50 text-cyan-700",
  emerald: "bg-emerald-50 text-emerald-700",
  violet: "bg-violet-50 text-violet-700",
  amber: "bg-amber-50 text-amber-700",
};

export default function BQLDocumentsPage() {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("Tất cả");
  const [page, setPage] = useState(1);
  const groups = ["Tất cả", ...Array.from(new Set(DOCUMENTS.map((item) => item.group)))];
  const visible = useMemo(() => {
    const keyword = query.trim().toLocaleLowerCase("vi");
    return DOCUMENTS.filter((item) =>
      (group === "Tất cả" || item.group === group) &&
      (!keyword || `${item.title} ${item.group}`.toLocaleLowerCase("vi").includes(keyword)),
    );
  }, [group, query]);
  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const paginated = visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const updateQuery = (value: string) => { setQuery(value); setPage(1); };
  const updateGroup = (value: string) => { setGroup(value); setPage(1); };

  return (
    <div>
      <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-[#173B75] via-[#1D4F91] to-[#137B91] px-6 py-7 text-white shadow-xl shadow-blue-950/15 sm:px-8">
        <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium ring-1 ring-white/20">
              <FileText className="h-3.5 w-3.5" /> Kho tri thức nội bộ
            </span>
            <h1 className="mt-4 text-2xl font-semibold tracking-tight sm:text-3xl">Tài liệu Ban quản lý</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-blue-100">
              Tra cứu nhanh quy trình vận hành và văn bản đang được Trợ lý AI sử dụng để hỗ trợ cư dân.
            </p>
          </div>
          <div className="rounded-2xl bg-white/10 px-5 py-3 text-center ring-1 ring-white/20">
            <strong className="block text-2xl">{DOCUMENTS.length}</strong>
            <span className="text-xs text-blue-100">tài liệu đã kiểm chứng</span>
          </div>
        </div>
      </section>

      <div className="mt-6 grid gap-3 sm:grid-cols-[1fr_auto]">
        <label className="flex h-12 items-center gap-3 rounded-xl border border-[#B6C4D6] bg-white px-4 shadow-sm focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/10">
          <Search className="h-4 w-4 text-slate-500" />
          <input value={query} onChange={(event) => updateQuery(event.target.value)} placeholder="Tìm tên tài liệu hoặc nhóm..." className="min-w-0 flex-1 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400" />
        </label>
        <select value={group} onChange={(event) => updateGroup(event.target.value)} className="h-12 rounded-xl border border-[#B6C4D6] bg-white px-4 text-sm text-slate-700 outline-none focus:border-blue-500">
          {groups.map((item) => <option key={item}>{item}</option>)}
        </select>
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-white/90 bg-white shadow-soft ring-1 ring-[#B6C4D6]/60">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 sm:px-6">
          <h2 className="font-semibold text-slate-800">Danh mục tài liệu</h2>
          <span className="text-xs font-medium text-slate-500">{visible.length} kết quả</span>
        </div>
        {visible.length ? (
          <div className="divide-y divide-slate-200">
            {paginated.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.title} className="flex items-center gap-4 px-5 py-5 transition hover:bg-blue-50/40 sm:px-6">
                  <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${TONE[item.tone]}`}><Icon className="h-5 w-5" /></div>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-semibold text-slate-800">{item.title}</h3>
                    <p className="mt-1 text-xs text-slate-500">{item.group} · {item.version}</p>
                  </div>
                  <span className="hidden rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-700 sm:inline-flex">Đã kiểm chứng</span>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="px-6 py-14 text-center text-sm text-slate-500">Không tìm thấy tài liệu phù hợp.</div>
        )}
        <Pagination page={page} pageCount={pageCount} onChange={setPage} />
      </div>

      <p className="mt-4 text-xs leading-5 text-slate-500">
        Trang hiện cung cấp danh mục tra cứu. Chức năng thêm, sửa và tải tệp cần API quản trị tài liệu do backend triển khai.
      </p>
    </div>
  );
}
