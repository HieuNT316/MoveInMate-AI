"use client";

import { useState } from "react";
import { Loader2, X } from "lucide-react";

import {
  api,
  ApiError,
  type AdminApplication,
  type ApplicationStatus,
} from "../../lib/api";
import { useToast } from "./Toast";

const STATUS_OPTIONS: { value: ApplicationStatus; label: string }[] = [
  { value: "received", label: "Đã tiếp nhận" },
  { value: "processing", label: "Đang xử lý" },
  { value: "needs_info", label: "Cần bổ sung" },
  { value: "approved", label: "Đã duyệt" },
  { value: "delivered", label: "Đã trả kết quả" },
  { value: "rejected", label: "Từ chối" },
];

/**
 * US-13 — BQL đổi trạng thái một hồ sơ. Không ép thứ tự chuyển trạng thái
 * (backend cho quay lại `needs_info` sau khi đã `approved`), nên hiện đủ cả
 * 6 lựa chọn thay vì chỉ "bước tiếp theo".
 */
export default function UpdateApplicationStatusDialog({
  userId,
  application,
  onClose,
  onUpdated,
}: {
  userId: number;
  application: AdminApplication;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const toast = useToast();
  const [status, setStatus] = useState<ApplicationStatus>(application.status);
  const [bqlNote, setBqlNote] = useState(application.bql_note ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (saving) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateApplicationStatus(userId, application.application_id, {
        status,
        bql_note: bqlNote.trim() || undefined,
      });
      onUpdated();
      toast.show("Đã lưu thay đổi");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError(
          "Hồ sơ tự khai này chưa có ảnh minh chứng — không thể ghi nhận khi chưa thấy bằng chứng.",
        );
      } else {
        setError("Không cập nhật được trạng thái, thử lại sau.");
      }
      toast.show("Cập nhật trạng thái hồ sơ không thành công", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F172A]/40 px-4">
      <div className="w-full max-w-md rounded-2xl border border-[#B6C4D6] bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-lg font-semibold text-[#1E293B]">
            Cập nhật trạng thái
          </h3>
          <button
            onClick={onClose}
            aria-label="Đóng"
            className="flex h-8 w-8 items-center justify-center rounded-full text-[#64748B] transition hover:bg-[#F8FAFC] hover:text-[#1E293B]"
          >
            <X className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>

        <p className="mt-1 text-sm text-[#475569]">
          {application.task_name} · {application.full_name} — {application.apartment}
        </p>

        <label className="mt-4 block">
          <span className="mb-1.5 block text-xs font-medium text-[#475569]">Trạng thái</span>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as ApplicationStatus)}
            className="w-full rounded-xl border border-[#B6C4D6] bg-white px-3.5 py-2.5 text-sm text-[#1E293B] focus:border-[#2563EB]/50 focus:outline-none focus:ring-1 focus:ring-[#2563EB]/30"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <label className="mt-4 block">
          <span className="mb-1.5 block text-xs font-medium text-[#475569]">
            Ghi chú cho cư dân (tuỳ chọn)
          </span>
          <textarea
            value={bqlNote}
            onChange={(event) => setBqlNote(event.target.value)}
            placeholder="Vd. Thiếu bản sao đăng ký xe"
            rows={3}
            maxLength={1000}
            className="w-full resize-none rounded-xl border border-[#B6C4D6] bg-white px-3.5 py-2.5 text-sm text-[#1E293B] focus:border-[#2563EB]/50 focus:outline-none focus:ring-1 focus:ring-[#2563EB]/30"
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
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-[#2563EB] py-3 text-sm font-medium text-white transition hover:bg-[#1D4ED8] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {saving ? "Đang lưu..." : "Lưu"}
        </button>
      </div>
    </div>
  );
}
