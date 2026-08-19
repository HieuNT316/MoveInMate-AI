"use client";

import {
  AlertCircle,
  CheckCircle2,
  CircleDashed,
  CircleDot,
  Lock,
  Upload,
  X,
  type LucideIcon,
} from "lucide-react";

import Layout from "../components/Layout";
import {
  DOCUMENT_STATUS_LABEL,
  mockDocuments,
  type DocumentStatus,
  type MockDocument,
} from "../../lib/mockDocuments";

const GROUP_LABEL: Record<MockDocument["group"], string> = {
  identity: "Giấy tờ định danh",
  residency: "Hộ khẩu & Cư trú",
  contract: "Hợp đồng",
  vehicle: "Phương tiện",
  other: "Khác",
};

const STATUS_STYLE: Record<DocumentStatus, string> = {
  not_submitted: "border-border bg-background text-muted",
  pending_review: "border-gold/40 bg-gold-tint text-gold",
  approved: "border-emerald/40 bg-emerald/10 text-emerald",
  rejected: "border-red-200 bg-red-50 text-red-700",
};

const STATUS_ICON: Record<DocumentStatus, LucideIcon> = {
  not_submitted: CircleDot,
  pending_review: CircleDashed,
  approved: CheckCircle2,
  rejected: X,
};

function groupDocs(docs: MockDocument[]) {
  const order: MockDocument["group"][] = [
    "identity",
    "residency",
    "contract",
    "vehicle",
    "other",
  ];
  return order
    .map((group) => ({ group, docs: docs.filter((d) => d.group === group) }))
    .filter((g) => g.docs.length > 0);
}

export default function DocumentsPage() {
  const groups = groupDocs(mockDocuments);

  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        <h2 className="font-display text-xl font-semibold text-ink">
          Hồ sơ & Giấy tờ
        </h2>
        <p className="mt-1 text-sm text-muted">
          Tất cả ({mockDocuments.length})
        </p>

        <div className="mt-6 space-y-8">
          {groups.map(({ group, docs }) => (
            <div key={group}>
              <h3 className="mb-3 text-xs font-medium uppercase tracking-[0.14em] text-muted">
                {GROUP_LABEL[group]}
              </h3>

              <div className="space-y-4">
                {docs.map((doc) => (
                  <div
                    key={doc.id}
                    className="interactive-card rounded-2xl border border-white/90 bg-surface/95 p-5 shadow-soft ring-1 ring-border/50"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium text-ink">
                        {doc.name}
                      </p>
                      {doc.required && (
                        <span className="rounded-full bg-red-50 px-2 py-0.5 text-[11px] text-red-600">
                          Bắt buộc
                        </span>
                      )}
                      <span
                        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLE[doc.status]}`}
                      >
                        {(() => {
                          const Icon = STATUS_ICON[doc.status];
                          return <Icon className="h-3 w-3" strokeWidth={2} />;
                        })()}
                        {DOCUMENT_STATUS_LABEL[doc.status]}
                      </span>
                    </div>

                    {doc.note && (
                      <p className="mt-1.5 text-sm text-muted">{doc.note}</p>
                    )}

                    {doc.rejectReason && (
                      <p className="mt-2 flex items-start gap-1.5 text-xs text-red-600">
                        <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" strokeWidth={2} />
                        {doc.rejectReason}
                      </p>
                    )}

                    {doc.files.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-3">
                        {doc.files.map((file) => (
                          <div
                            key={file.name}
                            className="w-28 rounded-lg border border-border bg-background p-2.5 text-center"
                          >
                            <p className="truncate text-[11px] text-ink/90">
                              {file.name}
                            </p>
                            <p className="text-[10px] text-muted">
                              {file.sizeKb} KB
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <button
                        disabled
                        className="mt-3 flex w-full flex-col items-center gap-1.5 rounded-lg border border-dashed border-border py-6 text-xs text-muted opacity-70"
                      >
                        <Upload className="h-4 w-4" strokeWidth={1.75} />
                        Chụp ảnh hoặc chọn file để tải lên
                        <span className="text-[10px] text-muted/70">
                          JPG, PNG, HEIC, PDF · Tối đa 5 file · Mỗi file ≤ 10 MB
                        </span>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 flex items-start gap-2.5 rounded-2xl border border-border bg-background px-5 py-4 text-xs text-muted">
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
          <p>
            <span className="font-medium text-ink">Bảo mật:</span> đây là dữ
            liệu minh hoạ cho UI Phase 2 (US-10) — chưa nối backend thật. Khi
            có API thật, giấy tờ cần được mã hoá và giới hạn quyền truy cập
            chỉ BQL và cư dân liên quan.
          </p>
        </div>
      </div>
    </Layout>
  );
}
