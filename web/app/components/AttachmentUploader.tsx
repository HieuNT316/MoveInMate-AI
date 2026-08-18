"use client";

import { useRef, useState } from "react";
import { FileText, Loader2, Paperclip } from "lucide-react";

import { api, ApiError, type Attachment } from "../../lib/api";
import { useToast } from "./Toast";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf"];
const MAX_BYTES = 5 * 1024 * 1024;

function formatSize(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

/**
 * US-13 mục 7 — tải ảnh/PDF minh chứng cho một hồ sơ đã nộp. Đây là giấy tờ
 * tuỳ thân (CCCD, VNeID...): KHÔNG log tên tệp hay nội dung ra console,
 * KHÔNG cache `url` (hết hạn sau vài phút — luôn đọc lại từ hồ sơ mới nhất).
 */
export default function AttachmentUploader({
  userId,
  applicationId,
  attachments,
  required,
  onUploaded,
}: {
  userId: number;
  applicationId: number;
  attachments: Attachment[];
  /** true với hồ sơ `self_declared` — ảnh CHÍNH LÀ nội dung nộp, không phải
   * tuỳ chọn (xem docs/CONTRACT_US13.md mục 2). */
  required?: boolean;
  onUploaded: () => void;
}) {
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pick = () => inputRef.current?.click();

  const handleFile = async (file: File) => {
    setError(null);
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Chỉ nhận ảnh JPG, PNG hoặc file PDF.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError(`Tệp vượt quá ${MAX_BYTES / (1024 * 1024)}MB.`);
      return;
    }

    setUploading(true);
    try {
      await api.uploadAttachment(userId, applicationId, file);
      onUploaded();
      toast.show("Đã lưu thay đổi");
    } catch (err) {
      if (err instanceof ApiError && err.status === 415) {
        setError("Chỉ nhận ảnh JPG, PNG hoặc file PDF.");
      } else if (err instanceof ApiError && err.status === 413) {
        setError("Tệp quá lớn — giới hạn 5MB.");
      } else {
        setError("Không tải lên được lúc này, thử lại sau.");
      }
      toast.show("Tải ảnh minh chứng không thành công", "error");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="mt-2">
      {attachments.length > 0 && (
        <ul className="space-y-1">
          {attachments.map((att) => (
            <li
              key={att.attachment_id}
              className="flex items-center gap-1.5 text-[11px] text-muted"
            >
              <FileText className="h-3 w-3 shrink-0 text-gold" strokeWidth={1.75} />
              {att.url ? (
                <a
                  href={att.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="truncate text-ink/70 underline decoration-dotted hover:text-gold"
                >
                  {att.filename}
                </a>
              ) : (
                <span className="truncate">{att.filename}</span>
              )}
              <span className="shrink-0">· {formatSize(att.size_bytes)}</span>
            </li>
          ))}
        </ul>
      )}

      {required && attachments.length === 0 && (
        <p className="mt-1 text-[11px] text-red-600">
          Bắt buộc — thủ tục này không có hồ sơ giấy, ảnh minh chứng là nội dung nộp.
        </p>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_TYPES.join(",")}
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = ""; // cho chọn lại đúng tệp vừa chọn nếu lỗi
          if (file) handleFile(file);
        }}
      />

      <button
        type="button"
        onClick={pick}
        disabled={uploading}
        className="mt-1.5 flex items-center gap-1.5 text-[11px] font-medium text-gold transition hover:text-gold-soft disabled:opacity-50"
      >
        {uploading ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Paperclip className="h-3 w-3" strokeWidth={2} />
        )}
        {uploading ? "Đang tải lên..." : "Tải ảnh minh chứng"}
      </button>

      {error && <p className="mt-1 text-[11px] text-red-600">{error}</p>}
    </div>
  );
}
