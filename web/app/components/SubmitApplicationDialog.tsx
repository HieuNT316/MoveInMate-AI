"use client";

import { useState } from "react";
import { Loader2, X } from "lucide-react";

import { api, ApiError, type ChecklistItem } from "../../lib/api";

/**
 * US-13 — nộp hồ sơ cho một mục checklist. Chỉ tạo hồ sơ (JSON) ở bước này;
 * ảnh minh chứng đính kèm sau qua endpoint riêng (xem docs/CONTRACT_US13.md
 * mục 7) — chưa làm ở component này.
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
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (saving) return;
    setSaving(true);
    setError(null);
    try {
      await api.createApplication(userId, {
        checklist_item_id: item.id,
        note: note.trim() || undefined,
      });
      onSubmitted();
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

        {item.handling_department && (
          <p className="mt-3 rounded-xl border border-border bg-background px-3.5 py-2.5 text-xs text-muted">
            <span className="font-medium text-ink">{item.handling_department}</span>
            {item.submission_location && <> · {item.submission_location}</>}
            {item.processing_time && <> · {item.processing_time}</>}
          </p>
        )}

        <label className="mt-4 block">
          <span className="mb-1.5 block text-xs font-medium text-muted">
            Ghi chú (tuỳ chọn)
          </span>
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Vd. biển số xe cần đăng ký thẻ"
            rows={3}
            maxLength={1000}
            className="w-full resize-none rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-ink focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
          />
        </label>

        {error && (
          <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          onClick={submit}
          disabled={saving}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-medium text-white transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "Đang nộp..." : "Nộp hồ sơ"}
        </button>
      </div>
    </div>
  );
}
