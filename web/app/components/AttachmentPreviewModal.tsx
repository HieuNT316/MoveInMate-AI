"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Image from "next/image";
import { ExternalLink, FileText, Loader2, X } from "lucide-react";
import { api, type Attachment } from "../../lib/api";

export default function AttachmentPreviewModal({ userId, applicationId, attachment, onClose }: { userId: number; applicationId: number; attachment: Attachment; onClose: () => void }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    api.getAttachmentUrl(userId, applicationId, attachment.attachment_id)
      .then((result) => { if (active) setUrl(result.url); })
      .catch(() => { if (active) setError("Không tải được giấy tờ. Vui lòng đóng và thử lại."); });
    return () => { active = false; };
  }, [userId, applicationId, attachment.attachment_id]);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previous; };
  }, []);

  const isImage = attachment.content_type.startsWith("image/");
  return createPortal(<div className="fixed inset-0 z-[70] flex items-center justify-center overscroll-none bg-slate-950/75 p-3 sm:p-6" role="dialog" aria-modal="true" aria-label={`Xem ${attachment.filename}`} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="flex h-[92dvh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
      <header className="flex items-center gap-3 border-b border-slate-200 px-4 py-3 sm:px-5">
        <FileText className="h-5 w-5 shrink-0 text-blue-600" />
        <div className="min-w-0 flex-1"><h2 className="truncate text-sm font-semibold text-slate-800">{attachment.filename}</h2><p className="text-[11px] text-slate-500">{attachment.content_type}</p></div>
        {url && <a href={url} target="_blank" rel="noopener noreferrer" className="hidden items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 sm:flex"><ExternalLink className="h-3.5 w-3.5" />Mở tab mới</a>}
        <button onClick={onClose} aria-label="Đóng xem giấy tờ" className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
      </header>
      <main className="flex min-h-0 flex-1 items-center justify-center bg-slate-100">
        {!url && !error && <div className="flex items-center gap-2 text-sm text-slate-600"><Loader2 className="h-5 w-5 animate-spin" />Đang tải giấy tờ...</div>}
        {error && <div className="mx-4 rounded-xl border border-red-200 bg-white px-6 py-5 text-center text-sm text-red-700">{error}</div>}
        {url && isImage && <div className="relative h-full w-full"><Image src={url} alt={attachment.filename} fill unoptimized className="object-contain" /></div>}
        {url && !isImage && <iframe src={url} title={attachment.filename} className="h-full w-full border-0" />}
      </main>
      {url && <footer className="border-t border-slate-200 px-4 py-2.5 text-center sm:hidden"><a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-700"><ExternalLink className="h-3.5 w-3.5" />Mở trong tab mới nếu không xem được</a></footer>}
    </div>
  </div>, document.body);
}
