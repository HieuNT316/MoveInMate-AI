"use client";

import { Bot, Send, ShieldAlert } from "lucide-react";

import Layout from "../components/Layout";
import {
  REQUEST_STATUS_LABEL,
  mockRequests,
  type RequestStatus,
} from "../../lib/mockRequests";

const STATUS_STYLE: Record<RequestStatus, string> = {
  submitted: "border-border bg-background text-muted",
  in_review: "border-gold/40 bg-gold-tint text-gold",
  approved: "border-emerald/40 bg-emerald/10 text-emerald",
  completed: "border-emerald/40 bg-emerald/10 text-emerald",
};

export default function RequestsPage() {
  const inProgress = mockRequests.filter((r) => r.status !== "completed");
  const needsReview = mockRequests.some((r) => r.needsBqlReview);

  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="font-display text-xl font-semibold text-ink">
              Yêu cầu của tôi
            </h2>
            <p className="mt-1 text-sm text-muted">
              {mockRequests.length} yêu cầu đã gửi · {inProgress.length} đang
              xử lý
            </p>
          </div>
        </div>

        {needsReview && (
          <div className="mt-6 flex items-start gap-3 rounded-2xl border border-gold/40 bg-gold-tint px-5 py-4 text-sm text-ink/80">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-gold" strokeWidth={1.75} />
            <p>
              <span className="font-medium text-ink">
                Cần xác nhận của Ban Quản Lý (HITL).
              </span>{" "}
              Một số yêu cầu cần BQL xem hồ sơ giấy tờ trực tiếp. BQL sẽ liên
              hệ trong vòng 1–2 ngày làm việc.
            </p>
          </div>
        )}

        <div className="mt-6 space-y-3">
          {mockRequests.map((req) => (
            <div
              key={req.id}
              className="flex items-center justify-between rounded-2xl border border-border bg-surface px-5 py-4"
            >
              <div className="flex items-center gap-3.5">
                <div className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-background text-ink/60">
                  <Send className="h-4 w-4" strokeWidth={1.75} />
                </div>
                <div>
                  <p className="text-sm font-medium text-ink">{req.title}</p>
                  <p className="text-xs text-muted">
                    {req.department} · {req.code}
                  </p>
                </div>
              </div>

              <div className="text-right">
                <span
                  className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${STATUS_STYLE[req.status]}`}
                >
                  {REQUEST_STATUS_LABEL[req.status]}
                </span>
                <p className="mt-1.5 text-[11px] text-muted">
                  Cập nhật: {req.updatedAt}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 rounded-2xl bg-ink px-6 py-6 text-white">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Bot className="h-4 w-4 text-gold-soft" strokeWidth={1.75} />
            Hỏi MoveInMate AI để tự động tạo yêu cầu mới
          </div>
          <form className="mt-3 flex gap-2">
            <input
              disabled
              placeholder="Ví dụ: Tôi muốn đăng ký thẻ xe máy cho 2 xe"
              className="w-full rounded-lg border border-white/15 bg-white/5 px-4 py-2.5 text-sm text-white placeholder:text-white/40 focus:outline-none"
            />
            <button
              disabled
              className="shrink-0 rounded-lg bg-gold px-4 py-2.5 text-sm font-medium text-ink opacity-60"
            >
              Tạo yêu cầu →
            </button>
          </form>
          <p className="mt-2 text-xs text-white/40">
            Agent sẽ tự động điền thông tin và định tuyến đến đúng bộ phận —
            tính năng Phase 2 (US-11), chưa nối backend.
          </p>
        </div>
      </div>
    </Layout>
  );
}
