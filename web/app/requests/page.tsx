"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, FileText, Loader2, Send } from "lucide-react";

import Layout from "../components/Layout";
import AttachmentUploader from "../components/AttachmentUploader";
import { api, type Application } from "../../lib/api";
import { useDemoUser } from "../../lib/useDemoUser";
import { applicationStatusLabel, applicationStatusTone } from "../../lib/applicationStatus";

const OPEN_STATUSES: Application["status"][] = ["received", "processing", "needs_info"];

export default function RequestsPage() {
  const { userId, ready } = useDemoUser();
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setApplications(await api.getApplications(userId));
      setError(null);
    } catch {
      setError("Không kết nối được backend. Chạy `uvicorn src.main:app --reload` chưa?");
    }
  }, [userId]);

  useEffect(() => {
    if (ready) load();
  }, [ready, load]);

  if (error) {
    return (
      <Layout>
        <p className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error}
        </p>
      </Layout>
    );
  }

  if (!applications) {
    return (
      <Layout>
        <div className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Đang tải hồ sơ đã nộp...
        </div>
      </Layout>
    );
  }

  const open = applications.filter((app) => OPEN_STATUSES.includes(app.status));
  const needsAction = applications.filter((app) => app.status === "needs_info");

  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="font-display text-xl font-semibold text-ink">
              Hồ sơ đã nộp
            </h2>
            <p className="mt-1 text-sm text-muted">
              {applications.length} hồ sơ đã nộp · {open.length} đang xử lý
            </p>
          </div>
        </div>

        {needsAction.length > 0 && (
          <div className="mt-6 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={1.75} />
            <p>
              <span className="font-medium">
                {needsAction.length} hồ sơ cần bạn bổ sung minh chứng.
              </span>{" "}
              Xem chi tiết bên dưới.
            </p>
          </div>
        )}

        {applications.length === 0 ? (
          <div className="mt-8 flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-surface px-6 py-14 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full border border-border bg-background text-ink/40">
              <Send className="h-5 w-5" strokeWidth={1.75} />
            </div>
            <p className="text-sm text-muted">
              Chưa có hồ sơ nào. Vào{" "}
              <a href="/checklist" className="font-medium text-gold hover:underline">
                Checklist
              </a>{" "}
              để nộp hồ sơ cho các thủ tục do Ban quản lý xử lý.
            </p>
          </div>
        ) : (
          <div className="mt-6 space-y-3">
            {applications.map((app) => (
              <div
                key={app.application_id}
                className="rounded-2xl border border-border bg-surface px-5 py-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3.5">
                    <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border bg-background text-ink/60">
                      <FileText className="h-4 w-4" strokeWidth={1.75} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-ink">{app.task_name}</p>
                      {app.handling_department && (
                        <p className="mt-0.5 text-xs text-muted">
                          {app.handling_department}
                          {app.submission_location && <> · {app.submission_location}</>}
                        </p>
                      )}
                      {app.note && (
                        <p className="mt-1.5 text-xs text-muted">Ghi chú: {app.note}</p>
                      )}
                    </div>
                  </div>

                  <span
                    className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${applicationStatusTone(app.status)}`}
                  >
                    {applicationStatusLabel(app)}
                  </span>
                </div>

                {app.bql_note &&
                  (app.status === "needs_info" || app.status === "rejected") && (
                    <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs text-red-700">
                      {app.bql_note}
                    </p>
                  )}

                <div className="mt-3 border-t border-border pt-3">
                  <AttachmentUploader
                    userId={userId}
                    applicationId={app.application_id}
                    attachments={app.attachments}
                    required={app.kind === "self_declared"}
                    onUploaded={load}
                  />
                </div>

                <p className="mt-2 text-[11px] text-muted">
                  Cập nhật: {new Date(app.updated_at).toLocaleString("vi-VN")}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
