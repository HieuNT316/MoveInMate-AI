"use client";

import { useState } from "react";
import { CheckCircle2, Loader2, ShieldAlert, X } from "lucide-react";

import { api, ApiError, type Application, type ChecklistItem } from "../../lib/api";
import {
  composeNote,
  getApplicationFormFields,
  getRequiredDocument,
} from "../../lib/applicationForms";
import AttachmentUploader from "./AttachmentUploader";

/**
 * US-13 — nộp hồ sơ cho một mục checklist, hai bước.
 *
 * `item.item_type` quyết định `kind` phía backend (routes.py: `bql_actionable`
 * → `bql_processing`, còn lại → `self_declared` — xem docs/CONTRACT_US13.md
 * mục 2), nên FE suy ra được TRƯỚC khi nộp:
 * - `third_party_info` (tạm trú, cập nhật cư trú...): không có form nghiệp
 *   vụ — ảnh minh chứng CHÍNH LÀ nội dung nộp.
 * - `bql_actionable` cần giấy tờ thật (thẻ cư dân, thẻ xe...): có form theo
 *   thủ tục (`lib/applicationForms.ts`) VÀ bắt buộc ảnh giấy tờ tương ứng —
 *   nộp form suông không kèm ảnh cà vẹt/CCCD thì BQL không có gì đối chiếu.
 * - `bql_actionable` không cần giấy tờ (kích hoạt tiện ích theo gói đã đăng
 *   ký, đặt lịch chuyển đồ...): chỉ cần form, không chặn bằng ảnh.
 *
 * Backend chỉ nhận ảnh SAU khi hồ sơ đã tồn tại (mục 7 — endpoint tách
 * riêng, cần `application_id`), nên bước 2 tạo hồ sơ trước rồi mới tải ảnh
 * ngay trong cùng dialog, thay vì bắt cư dân tự quay lại tìm nút sau.
 */
export default function SubmitApplicationDialog({
  userId,
  item,
  onClose,
  onSubmitted,
}: {
  userId: number;
  item: ChecklistItem;
  onClose: () => void;
  onSubmitted: () => void;
}) {
  const isSelfDeclared = item.item_type !== "bql_actionable";
  const fields = isSelfDeclared ? null : getApplicationFormFields(item.task_name);
  const requiredDocument = isSelfDeclared
    ? "Đơn đăng ký hoặc ảnh chụp màn hình VNeID"
    : getRequiredDocument(item.task_name);

  const [values, setValues] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sau khi tạo hồ sơ, dialog chuyển sang bước tải ảnh nếu thủ tục cần giấy
  // tờ. `createdApp` khác null nghĩa là bước 1 đã xong, không quay lại được.
  const [createdApp, setCreatedApp] = useState<Application | null>(null);
  const [attachmentCount, setAttachmentCount] = useState(0);

  const missingRequired =
    fields?.some((f) => f.required && !values[f.key]?.trim()) ?? false;

  const submit = async () => {
    if (saving || missingRequired) return;
    setSaving(true);
    setError(null);
    try {
      const composedNote = fields ? composeNote(fields, values, note) : note.trim() || undefined;
      const app = await api.createApplication(userId, {
        checklist_item_id: item.id,
        note: composedNote,
      });
      if (requiredDocument) {
        setCreatedApp(app);
      } else {
        onSubmitted();
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Mục này đã có hồ sơ đang xử lý — không nộp trùng được.");
      } else if (err instanceof ApiError && err.status === 404) {
        setError("Mục này không có trong checklist của bạn.");
      } else {
        setError("Không nộp được hồ sơ lúc này, thử lại sau.");
      }
    } finally {
      setSaving(false);
    }
  };

  // Hồ sơ đã tồn tại ở backend rồi (kể cả khi chưa tải ảnh) — đóng dialog ở
  // bước này vẫn phải báo cho checklist tải lại, không phải huỷ thao tác.
  const closeAfterCreated = () => onSubmitted();

  if (createdApp) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-xl">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-lg font-semibold text-ink">
              Tải ảnh minh chứng
            </h3>
            <button
              onClick={closeAfterCreated}
              aria-label="Đóng"
              className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition hover:bg-background hover:text-ink"
            >
              <X className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </div>

          <p className="mt-1 text-sm text-muted">{item.task_name}</p>

          <div className="mt-3 flex items-start gap-2.5 rounded-xl border border-gold/40 bg-gold-tint px-3.5 py-3 text-xs text-ink/80">
            <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gold" strokeWidth={1.75} />
            <p>
              Hồ sơ đã ghi nhận, nhưng cần <span className="font-medium text-ink">{requiredDocument}</span> để
              Ban quản lý đối chiếu — nộp form suông không có gì để xác nhận.
            </p>
          </div>

          <div className="mt-4 rounded-xl border border-border bg-background px-3.5 py-3">
            <AttachmentUploader
              userId={userId}
              applicationId={createdApp.application_id}
              attachments={[]}
              required
              onUploaded={() => setAttachmentCount((c) => c + 1)}
            />
          </div>

          {attachmentCount > 0 && (
            <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-emerald">
              <CheckCircle2 className="h-3.5 w-3.5" strokeWidth={1.75} />
              Đã tải {attachmentCount} ảnh.
            </p>
          )}

          <button
            onClick={closeAfterCreated}
            disabled={attachmentCount === 0}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-medium text-white transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-40"
          >
            Hoàn tất
          </button>
          {attachmentCount === 0 && (
            <p className="mt-2 text-center text-[11px] text-muted">
              Tải ít nhất một ảnh để hoàn tất — có thể quay lại bổ sung sau ở trang Checklist.
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-lg font-semibold text-ink">
            Nộp hồ sơ
          </h3>
          <button
            onClick={onClose}
            aria-label="Đóng"
            className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition hover:bg-background hover:text-ink"
          >
            <X className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>

        <p className="mt-1 text-sm text-muted">{item.task_name}</p>

        {isSelfDeclared ? (
          <div className="mt-3 flex items-start gap-2.5 rounded-xl border border-gold/40 bg-gold-tint px-3.5 py-3 text-xs text-ink/80">
            <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gold" strokeWidth={1.75} />
            <p>
              Thủ tục này thuộc phạm vi <span className="font-medium text-ink">cơ quan công an</span>,
              Ban quản lý chỉ ghi nhận. Bấm xác nhận rồi tải lên đơn đăng ký hoặc ảnh chụp màn
              hình VNeID ở bước tiếp theo — ảnh minh chứng là nội dung nộp, bắt buộc.
            </p>
          </div>
        ) : (
          <>
            {item.handling_department && (
              <p className="mt-3 rounded-xl border border-border bg-background px-3.5 py-2.5 text-xs text-muted">
                <span className="font-medium text-ink">{item.handling_department}</span>
                {item.submission_location && <> · {item.submission_location}</>}
                {item.processing_time && <> · {item.processing_time}</>}
              </p>
            )}

            {requiredDocument && (
              <p className="mt-3 rounded-xl border border-gold/40 bg-gold-tint px-3.5 py-2.5 text-xs text-ink/80">
                Cần kèm <span className="font-medium text-ink">{requiredDocument}</span> ở bước
                tiếp theo — bắt buộc để BQL đối chiếu.
              </p>
            )}

            {fields && (
              <div className="mt-4 space-y-3">
                {fields.map((f) => (
                  <label key={f.key} className="block">
                    <span className="mb-1.5 block text-xs font-medium text-muted">
                      {f.label}
                      {f.required && <span className="text-red-600"> *</span>}
                    </span>
                    {f.type === "select" ? (
                      <select
                        value={values[f.key] ?? ""}
                        onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                        className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-ink focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
                      >
                        <option value="">— Chọn —</option>
                        {f.options?.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={f.type}
                        value={values[f.key] ?? ""}
                        onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                        placeholder={f.placeholder}
                        className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-ink focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
                      />
                    )}
                  </label>
                ))}
              </div>
            )}
          </>
        )}

        {!isSelfDeclared && (
          <label className="mt-4 block">
            <span className="mb-1.5 block text-xs font-medium text-muted">
              Ghi chú thêm (tuỳ chọn)
            </span>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Vd. cần lắp đặt gấp"
              rows={2}
              maxLength={1000}
              className="w-full resize-none rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-ink focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
            />
          </label>
        )}

        {error && (
          <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          onClick={submit}
          disabled={saving || missingRequired}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-medium text-white transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving
            ? "Đang nộp..."
            : isSelfDeclared
              ? "Xác nhận, nộp minh chứng tiếp"
              : requiredDocument
                ? "Tiếp tục, tải ảnh giấy tờ"
                : "Nộp hồ sơ"}
        </button>
      </div>
    </div>
  );
}
