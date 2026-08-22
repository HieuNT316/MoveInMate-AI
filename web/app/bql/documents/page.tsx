"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Clock3, FileText, Loader2, Plus, RefreshCw, Search, TriangleAlert } from "lucide-react";
import { api, describeError, type AdminDocument, type EmbedStatus } from "../../../lib/api";
import { useDemoUser } from "../../../lib/useDemoUser";
import Pagination from "../../components/Pagination";

const PAGE_SIZE = 6;
const STATUS: Record<EmbedStatus, { label: string; style: string; icon: typeof Clock3 }> = {
  pending: { label: "Đang chờ", style: "border-amber-200 bg-amber-50 text-amber-700", icon: Clock3 },
  processing: { label: "Đang xử lý", style: "border-blue-200 bg-blue-50 text-blue-700", icon: Loader2 },
  ready: { label: "Sẵn sàng", style: "border-emerald-200 bg-emerald-50 text-emerald-700", icon: CheckCircle2 },
  failed: { label: "Thất bại", style: "border-red-200 bg-red-50 text-red-700", icon: TriangleAlert },
};

export default function BQLDocumentsPage() {
  const { userId, ready } = useDemoUser();
  const [documents, setDocuments] = useState<AdminDocument[] | null>(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async (quiet = false) => {
    try { setDocuments(await api.getAdminDocuments(userId)); setError(null); }
    catch (err) { if (!quiet) setError(describeError(err)); }
  }, [userId]);
  useEffect(() => { if (ready) void load(); }, [ready, load]);
  const active = documents?.some((doc) => doc.embed_status === "pending" || doc.embed_status === "processing");
  useEffect(() => {
    if (!ready || !active) return;
    const timer = window.setInterval(() => void load(true), 10000);
    return () => window.clearInterval(timer);
  }, [ready, active, load]);
  const visible = useMemo(() => {
    const keyword = query.trim().toLocaleLowerCase("vi");
    return (documents ?? []).filter((doc) => !keyword || doc.title.toLocaleLowerCase("vi").includes(keyword));
  }, [documents, query]);
  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const paginated = visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const submit = async () => {
    if (!title.trim() || !content.trim() || saving) return;
    setSaving(true); setError(null);
    try {
      const created = await api.createAdminDocument(userId, { title: title.trim(), content: content.trim() });
      setDocuments((current) => [created, ...(current ?? [])]);
      setTitle(""); setContent(""); setPage(1);
    } catch (err) { setError(describeError(err)); }
    finally { setSaving(false); }
  };
  return <div className="space-y-6">
    <section className="rounded-3xl bg-gradient-to-br from-[#173B75] via-[#1D4F91] to-[#137B91] px-6 py-7 text-white shadow-xl shadow-blue-950/15 sm:px-8">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-blue-100">Kho tri thức nội bộ</p><h1 className="mt-2 text-2xl font-semibold sm:text-3xl">Tài liệu Ban quản lý</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-blue-100">Dán quy trình đã kiểm chứng để bổ sung kiến thức cho Trợ lý AI. Hệ thống xử lý nền nên bạn có thể rời trang sau khi gửi.</p>
    </section>
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex items-center gap-2"><Plus className="h-5 w-5 text-blue-600" /><h2 className="font-semibold text-slate-800">Thêm tài liệu mới</h2></div>
      <div className="mt-4 grid gap-3"><input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={255} placeholder="Tiêu đề quy trình" className="rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-blue-500" /><textarea value={content} onChange={(e) => setContent(e.target.value)} rows={7} placeholder="Dán toàn bộ nội dung quy trình tại đây..." className="resize-y rounded-xl border border-slate-300 px-4 py-3 text-sm leading-6 outline-none focus:border-blue-500" /><div className="flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-slate-500">Trạng thái tự cập nhật mỗi 10 giây khi đang xử lý.</p><button onClick={submit} disabled={!title.trim() || !content.trim() || saving} title={!title.trim() || !content.trim() ? "Nhập đủ tiêu đề và nội dung để nạp tài liệu" : undefined} className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700">{saving && <Loader2 className="h-4 w-4 animate-spin" />}{saving ? "Đang gửi..." : "Nạp vào Trợ lý AI"}</button></div></div>
    </section>
    {error && <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div>}
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4 sm:px-6"><h2 className="font-semibold text-slate-800">Danh sách tài liệu <span className="text-sm font-normal text-slate-500">({visible.length})</span></h2><div className="flex items-center gap-2"><label className="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2"><Search className="h-4 w-4 text-slate-400" /><input value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} placeholder="Tìm tài liệu" className="w-40 bg-transparent text-sm outline-none" /></label><button onClick={() => void load()} aria-label="Làm mới" className="rounded-lg border border-slate-300 p-2.5 text-slate-600"><RefreshCw className="h-4 w-4" /></button></div></div>
      {!documents ? <div className="flex items-center justify-center gap-2 py-14 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />Đang tải tài liệu...</div> : paginated.length === 0 ? <div className="py-14 text-center text-sm text-slate-500">Chưa có tài liệu phù hợp.</div> : <div className="divide-y divide-slate-200">{paginated.map((doc) => <DocumentRow key={doc.document_id} document={doc} />)}</div>}
      <Pagination page={page} pageCount={pageCount} onChange={setPage} />
    </section>
  </div>;
}

function DocumentRow({ document }: { document: AdminDocument }) {
  const status = STATUS[document.embed_status]; const Icon = status.icon;
  return <article className="flex items-center gap-4 px-5 py-5 sm:px-6"><div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600"><FileText className="h-5 w-5" /></div><div className="min-w-0 flex-1"><h3 className="truncate text-sm font-semibold text-slate-800">{document.title}</h3><p className="mt-1 text-xs text-slate-500">Nạp lúc {new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" }).format(new Date(document.uploaded_at))}</p></div><span className={`flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${status.style}`}><Icon className={`h-3.5 w-3 ${document.embed_status === "processing" ? "animate-spin" : ""}`} />{status.label}</span></article>;
}
