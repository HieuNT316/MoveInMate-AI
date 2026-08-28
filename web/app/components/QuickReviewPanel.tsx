"use client";

import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, Check, CheckCircle2, Keyboard, Loader2, Paperclip, X, XCircle } from "lucide-react";

import { api, ApiError, type AdminApplication, type ApplicationStatus, type Attachment } from "../../lib/api";
import { applicationStatusLabel, applicationStatusTone } from "../../lib/applicationStatus";
import { useToast } from "./Toast";

const TEMPLATES = [
  "Ảnh giấy tờ bị mờ hoặc mất góc. Vui lòng chụp lại rõ toàn bộ giấy tờ.",
  "Thiếu mặt sau CCCD. Vui lòng bổ sung để Ban quản lý đối chiếu.",
  "Thông tin trên giấy tờ chưa trùng khớp với hồ sơ cư dân.",
  "Giấy tờ chưa có chữ ký. Vui lòng ký và tải lại bản hoàn chỉnh.",
];

export default function QuickReviewPanel({ userId, application, onClose, onReviewed }: { userId: number; application: AdminApplication; onClose: () => void; onReviewed: () => void }) {
  const toast = useToast();
  const [selected, setSelected] = useState<Attachment | null>(application.attachments[0] ?? null);
  const [status, setStatus] = useState<ApplicationStatus>(application.status);
  const [note, setNote] = useState(application.bql_note ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSelected(application.attachments[0] ?? null);
    setStatus(application.status);
    setNote(application.bql_note ?? "");
    setError(null);
  }, [application]);

  const submit = useCallback(async () => {
    if (saving) return;
    if ((status === "needs_info" || status === "rejected") && !note.trim()) {
      setError("Cần ghi rõ lý do để cư dân biết phải sửa gì.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.updateApplicationStatus(userId, application.application_id, { status, bql_note: note.trim() || undefined });
      toast.show("Đã xử lý hồ sơ — chuyển sang hồ sơ tiếp theo");
      onReviewed();
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? "Hồ sơ chưa có đủ minh chứng để duyệt." : "Không cập nhật được hồ sơ, vui lòng thử lại.");
      toast.show("Xử lý hồ sơ không thành công", "error");
    } finally { setSaving(false); }
  }, [application.application_id, note, onReviewed, saving, status, toast, userId]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.tagName === "SELECT";
      if (event.key === "Escape") onClose();
      if (typing) return;
      if (event.key.toLowerCase() === "a") setStatus("approved");
      if (event.key.toLowerCase() === "b") setStatus("needs_info");
      if (event.key.toLowerCase() === "t") setStatus("rejected");
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) void submit();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, submit]);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previous; };
  }, []);

  const missing = application.missing_documents ?? null;
  return createPortal(<div className="fixed inset-0 z-50 bg-slate-950/55 p-2 sm:p-4" role="dialog" aria-modal="true" aria-label="Duyệt nhanh hồ sơ">
    <div className="mx-auto flex h-full max-w-[1500px] flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
      <header className="flex items-center gap-3 border-b border-slate-200 px-4 py-3 sm:px-5">
        <div className="min-w-0 flex-1"><p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-blue-600">Duyệt nhanh · #{application.application_id}</p><h2 className="truncate text-base font-semibold text-slate-900">{application.task_name}</h2><p className="truncate text-xs text-slate-500">{application.full_name} · Căn {application.apartment}</p></div>
        <span className={`hidden rounded-full border px-3 py-1 text-xs sm:block ${applicationStatusTone(application.status)}`}>{applicationStatusLabel(application)}</span>
        <button type="button" onClick={onClose} aria-label="Đóng panel duyệt" className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
      </header>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[15rem_minmax(0,1fr)_22rem]">
        <aside className="overflow-y-auto border-b border-slate-200 bg-slate-50 p-3 lg:border-b-0 lg:border-r">
          <p className="mb-2 flex items-center gap-2 text-xs font-semibold text-slate-700"><Paperclip className="h-3.5 w-3.5" />Giấy tờ ({application.attachments.length})</p>
          {application.attachments.length === 0 ? <p className="rounded-lg border border-dashed border-amber-300 bg-amber-50 p-3 text-xs text-amber-800">Chưa có tệp để đối chiếu.</p> : <div className="flex gap-2 overflow-x-auto lg:flex-col lg:overflow-visible">{application.attachments.map((attachment) => <button key={attachment.attachment_id} type="button" onClick={() => setSelected(attachment)} className={`min-w-48 rounded-lg border p-3 text-left lg:min-w-0 ${selected?.attachment_id === attachment.attachment_id ? "border-blue-500 bg-blue-50 ring-2 ring-blue-100" : "border-slate-200 bg-white hover:border-blue-300"}`}><p className="truncate text-xs font-medium text-slate-800">{attachment.filename}</p><p className="mt-1 truncate text-[10px] text-slate-500">{attachment.document_type ?? "Chưa phân loại"}</p></button>)}</div>}
        </aside>

        <main className="relative min-h-[18rem] overflow-hidden bg-slate-200 lg:min-h-0">{selected ? <InlinePreview userId={userId} applicationId={application.application_id} attachment={selected} /> : <div className="flex h-full items-center justify-center text-sm text-slate-500">Chọn một giấy tờ để xem</div>}</main>

        <aside className="overflow-y-auto border-t border-slate-200 p-4 lg:border-l lg:border-t-0">
          <section><h3 className="text-sm font-semibold text-slate-900">Kiểm tra giấy tờ</h3>
            {missing === null ? <p className="mt-2 flex gap-2 rounded-lg bg-amber-50 p-3 text-xs text-amber-800"><AlertTriangle className="h-4 w-4 shrink-0" />Có tệp chưa phân loại, chưa thể kết luận hồ sơ đã đủ.</p> : missing.length > 0 ? <ul className="mt-2 space-y-2">{missing.map((doc) => <li key={doc.code} className="flex gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700"><XCircle className="h-4 w-4 shrink-0" />Thiếu {doc.label}</li>)}</ul> : <p className="mt-2 flex gap-2 rounded-lg bg-emerald-50 p-3 text-xs text-emerald-700"><CheckCircle2 className="h-4 w-4 shrink-0" />Không phát hiện giấy tờ còn thiếu.</p>}
          </section>

          <section className="mt-5"><h3 className="text-sm font-semibold text-slate-900">Kết quả xử lý</h3><div className="mt-2 grid grid-cols-3 gap-2"><ActionButton active={status === "approved"} tone="green" onClick={() => setStatus("approved")} icon={Check} label="Duyệt" /><ActionButton active={status === "needs_info"} tone="amber" onClick={() => setStatus("needs_info")} icon={AlertTriangle} label="Bổ sung" /><ActionButton active={status === "rejected"} tone="red" onClick={() => setStatus("rejected")} icon={XCircle} label="Từ chối" /></div></section>

          <section className="mt-5"><label htmlFor="quick-review-note" className="text-sm font-semibold text-slate-900">Phản hồi cho cư dân</label><textarea id="quick-review-note" value={note} onChange={(event) => setNote(event.target.value)} rows={4} maxLength={1000} placeholder="Ghi rõ nội dung cần bổ sung..." className="mt-2 w-full resize-none rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /><div className="mt-2 flex flex-wrap gap-1.5">{TEMPLATES.map((template, index) => <button key={template} type="button" onClick={() => { setNote(template); setStatus("needs_info"); }} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-left text-[10px] text-slate-600 hover:border-blue-300" title={template}>Mẫu {index + 1}</button>)}</div></section>

          {error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-xs text-red-700">{error}</p>}
          <button type="button" onClick={() => void submit()} disabled={saving} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}{saving ? "Đang lưu..." : "Lưu và hồ sơ tiếp theo"}</button>
          <div className="mt-3 hidden items-center gap-2 rounded-lg bg-slate-50 p-2 text-[10px] text-slate-500 xl:flex"><Keyboard className="h-3.5 w-3.5" /><span>A Duyệt · B Bổ sung · T Từ chối · Ctrl+Enter Lưu</span></div>
        </aside>
      </div>
    </div>
  </div>, document.body);
}

function ActionButton({ active, tone, onClick, icon: Icon, label }: { active: boolean; tone: "green" | "amber" | "red"; onClick: () => void; icon: typeof Check; label: string }) {
  const colors = { green: active ? "border-emerald-500 bg-emerald-50 text-emerald-700" : "border-slate-200 text-slate-600", amber: active ? "border-amber-500 bg-amber-50 text-amber-800" : "border-slate-200 text-slate-600", red: active ? "border-red-500 bg-red-50 text-red-700" : "border-slate-200 text-slate-600" };
  return <button type="button" onClick={onClick} className={`flex flex-col items-center gap-1 rounded-lg border px-2 py-2 text-[10px] font-medium ${colors[tone]}`}><Icon className="h-4 w-4" />{label}</button>;
}

function InlinePreview({ userId, applicationId, attachment }: { userId: number; applicationId: number; attachment: Attachment }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => { let active = true; setUrl(null); setError(false); api.getAttachmentUrl(userId, applicationId, attachment.attachment_id).then((result) => { if (active) setUrl(result.url); }).catch(() => { if (active) setError(true); }); return () => { active = false; }; }, [applicationId, attachment.attachment_id, userId]);
  if (error) return <div className="flex h-full items-center justify-center p-6 text-center text-sm text-red-700">Không mở được giấy tờ này.</div>;
  if (!url) return <div className="flex h-full items-center justify-center gap-2 text-sm text-slate-600"><Loader2 className="h-4 w-4 animate-spin" />Đang tải giấy tờ...</div>;
  // Signed URL private, có hạn dùng; không đưa qua image optimizer/cache của Next.
  // eslint-disable-next-line @next/next/no-img-element
  if (attachment.content_type.startsWith("image/")) return <img src={url} alt={attachment.filename} className="h-full w-full object-contain" />;
  return <iframe src={url} title={attachment.filename} className="h-full w-full border-0 bg-white" />;
}
