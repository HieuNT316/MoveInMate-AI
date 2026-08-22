"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, CalendarClock, FileCheck2, FileText, Paperclip, Plus, Upload } from "lucide-react";
import Layout from "../components/Layout";
import AttachmentUploader from "../components/AttachmentUploader";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { api, describeError, type Application } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { applicationStatusLabel, applicationStatusTone } from "../../lib/applicationStatus";

export default function DocumentsPage() {
  const { userId, ready } = useDemoUser();
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try { setApplications(await api.getApplications(userId)); setError(null); }
    catch (err) { setError(describeError(err)); }
  }, [userId]);
  useEffect(() => { if (ready) void load(); }, [ready, load]);

  return <Layout>
    <div className="mx-auto max-w-4xl">
      <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-[#173B75] via-[#1D4F91] to-[#137B91] px-6 py-7 text-white shadow-xl shadow-blue-950/15 sm:px-8">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div><p className="text-xs font-medium uppercase tracking-[0.14em] text-blue-100">Hồ sơ của bạn</p><h1 className="mt-2 text-2xl font-semibold sm:text-3xl">Giấy tờ đã nộp</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-blue-100">Theo dõi hồ sơ đã gửi, phản hồi của Ban quản lý và mở lại từng giấy tờ ngay trong app.</p></div>
          <Link href="/checklist" className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-blue-700 shadow-sm hover:bg-blue-50"><Plus className="h-4 w-4" />Nộp hồ sơ mới</Link>
        </div>
      </section>

      <div className="mt-6">
        {error && <ErrorState message={error} onRetry={load} />}
        {!error && !applications && <div className="flex items-center gap-2 py-10 text-sm text-muted"><span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />Đang tải hồ sơ...</div>}
        {applications?.length === 0 && <EmptyState icon={FileCheck2} title="Bạn chưa nộp hồ sơ nào" description="Vào Việc cần làm, chọn thủ tục phù hợp rồi tải giấy tờ để gửi Ban quản lý." />}
        {applications && applications.length > 0 && <div className="space-y-4">{applications.map((application) => <ApplicationCard key={application.application_id} userId={userId} application={application} onChanged={load} />)}</div>}
      </div>
    </div>
  </Layout>;
}

function ApplicationCard({ userId, application, onChanged }: { userId: number; application: Application; onChanged: () => void }) {
  const actionNeeded = application.status === "needs_info" || application.status === "rejected" || application.attachments.length === 0;
  return <article className={`rounded-2xl border bg-white p-5 shadow-soft sm:p-6 ${actionNeeded ? "border-amber-300 ring-2 ring-amber-100" : "border-white/90 ring-1 ring-border/50"}`}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex min-w-0 items-start gap-3"><div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600"><FileText className="h-5 w-5" /></div><div className="min-w-0"><h2 className="font-semibold text-ink">{application.task_name}</h2><p className="mt-1 flex items-center gap-1.5 text-xs text-muted"><CalendarClock className="h-3.5 w-3.5" />Cập nhật {formatDate(application.updated_at)}</p></div></div>
      <span className={`rounded-full border px-3 py-1 text-xs font-medium ${applicationStatusTone(application.status)}`}>{applicationStatusLabel(application)}</span>
    </div>

    {application.bql_note && <div className={`mt-4 flex items-start gap-2 rounded-xl px-4 py-3 text-sm ${actionNeeded ? "bg-amber-50 text-amber-900" : "bg-slate-50 text-slate-700"}`}><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><p><span className="font-semibold">Phản hồi BQL: </span>{application.bql_note}</p></div>}

    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
      <div className="flex items-center justify-between"><p className="flex items-center gap-2 text-sm font-semibold text-slate-800"><Paperclip className="h-4 w-4 text-blue-600" />Giấy tờ đã tải</p><span className="text-xs text-slate-500">{application.attachments.length} tệp</span></div>
      {application.attachments.length === 0 && <p className="mt-3 flex items-center gap-2 text-sm text-amber-800"><Upload className="h-4 w-4" />Chưa có giấy tờ. Hãy tải tệp để hoàn tất hồ sơ.</p>}
      <AttachmentUploader userId={userId} applicationId={application.application_id} attachments={application.attachments} required={application.kind === "self_declared"} onUploaded={onChanged} />
    </div>
    {application.note && <p className="mt-3 text-xs leading-5 text-muted"><span className="font-medium text-ink">Ghi chú khi nộp:</span> {application.note}</p>}
  </article>;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
