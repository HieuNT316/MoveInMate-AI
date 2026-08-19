"use client";

import { useRef, useState } from "react";
import { Check, FileText, Loader2, Paperclip } from "lucide-react";

import { api, ApiError, type Attachment } from "../../lib/api";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf"];
const MAX_BYTES = 5 * 1024 * 1024;

function formatSize(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

/**
 * US-13 mục 7 — tải ảnh/PDF minh chứng cho một hồ sơ đã nộp. Đây là giấy tờ
 * tuỳ thân (CCCD, VNeID...): KHÔNG log tên tệp hay nội dung ra console,
 * KHÔNG cache `url` (hết hạn sau vài phút — luôn đọc lại từ hồ sơ mới nhất).
 *
 * `requiredDocuments` — khi có, hiện thành CHECKLIST TỪNG LOẠI GIẤY TỜ thay
 * vì một nút tải chung chung. FE đã gửi `document_type` lên khi upload
 * (xem `api.uploadAttachment`) — ĐỀ XUẤT, chờ Hiếu thêm cột lưu ở backend.
 * Cho tới lúc đó, `resolveSlot()` tự rơi về khớp theo VỊ TRÍ (tệp thứ i ↔
 * mục thứ i) y hệt cách cũ. Khi backend bắt đầu trả `document_type` trong
 * response, khớp theo nhãn thật sẽ tự động thay thế — không cần sửa gì ở
 * đây nữa.
 */
export default function AttachmentUploader({
  userId,
  applicationId,
  attachments,
  required,
  requiredDocuments,
  onUploaded,
}: {
  userId: number;
  applicationId: number;
  attachments: Attachment[];
  /** true với hồ sơ `self_declared` không có `requiredDocuments` cụ thể — ảnh
   * CHÍNH LÀ nội dung nộp, không phải tuỳ chọn (xem docs/CONTRACT_US13.md mục 2). */
  required?: boolean;
  requiredDocuments?: string[];
  onUploaded: (attachment: Attachment) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  // Slot đang chờ chọn tệp — input file dùng chung cho mọi slot, cần nhớ
  // đang tải CHO nhãn nào để gắn `document_type` đúng lúc submit.
  const pendingSlotRef = useRef<string | undefined>(undefined);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pick = (slotLabel?: string) => {
    pendingSlotRef.current = slotLabel;
    inputRef.current?.click();
  };

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
      const created = await api.uploadAttachment(
        userId,
        applicationId,
        file,
        pendingSlotRef.current,
      );
      onUploaded(created);
    } catch (err) {
      if (err instanceof ApiError && err.status === 415) {
        setError("Chỉ nhận ảnh JPG, PNG hoặc file PDF.");
      } else if (err instanceof ApiError && err.status === 413) {
        setError("Tệp quá lớn — giới hạn 5MB.");
      } else {
        setError("Không tải lên được lúc này, thử lại sau.");
      }
    } finally {
      setUploading(false);
    }
  };

  // Backend hiện chưa trả `document_type` cho tệp nào cả → rơi về khớp vị
  // trí. Ngay khi có ít nhất 1 tệp mang nhãn thật, coi như backend đã hỗ
  // trợ và chuyển hẳn sang khớp theo nhãn (không trộn hai kiểu nửa vời).
  const labelsSupported = attachments.some((a) => a.document_type);

  const resolveSlot = (label: string, index: number): Attachment | undefined => {
    if (labelsSupported) return attachments.find((a) => a.document_type === label);
    return attachments[index];
  };

  return (
    <div className="mt-2">
      {requiredDocuments && requiredDocuments.length > 0 ? (
        <div className="space-y-1">
          <p className="text-[11px] font-medium text-muted">
            Đã tải{" "}
            {requiredDocuments.filter((label, index) => resolveSlot(label, index)).length}/
            {requiredDocuments.length} giấy tờ bắt buộc
          </p>
          <ul className="space-y-1">
            {requiredDocuments.map((label, index) => {
              const att = resolveSlot(label, index);
              const done = Boolean(att);
              // Chưa khớp theo nhãn thật được thì vẫn phải ép đúng thứ tự
              // (chỉ mở khoá đúng MỘT slot kế tiếp) để khớp vị trí không sai.
              // Có nhãn thật rồi thì slot nào thiếu cũng tải được, không cần
              // đúng thứ tự nữa.
              const isNext = !done && (labelsSupported || attachments.length === index);
              return (
                <li
                  key={label}
                  className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] ${
                    done
                      ? "border-emerald/30 bg-emerald/5 text-ink/85"
                      : isNext
                        ? "border-gold/40 bg-gold-tint text-ink"
                        : "border-border bg-background text-muted"
                  }`}
                >
                  {done ? (
                    <Check className="h-3 w-3 shrink-0 text-emerald" strokeWidth={2.5} />
                  ) : (
                    <span className="flex h-3 w-3 shrink-0 items-center justify-center text-[9px] font-semibold">
                      {index + 1}
                    </span>
                  )}

                  {att && att.url ? (
                    <a
                      href={att.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="min-w-0 flex-1 truncate underline decoration-dotted hover:text-gold"
                    >
                      {label}
                    </a>
                  ) : (
                    <span className="min-w-0 flex-1 truncate">{label}</span>
                  )}

                  {att && (
                    <span className="shrink-0 text-[10px] text-muted">
                      {formatSize(att.size_bytes)}
                    </span>
                  )}

                  {isNext && (
                    <button
                      type="button"
                      onClick={() => pick(label)}
                      disabled={uploading}
                      className="flex shrink-0 items-center gap-1 font-medium text-gold transition hover:text-gold-soft disabled:opacity-50"
                    >
                      {uploading ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Paperclip className="h-3 w-3" strokeWidth={2} />
                      )}
                      {uploading ? "Đang tải..." : "Tải ảnh"}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>

          {/* Tệp thừa (nếu có) vượt số slot khai báo — vẫn giữ lại, hiện gọn
              ở cuối thay vì mất dấu vết. */}
          {attachments.length > requiredDocuments.length && (
            <ul className="space-y-1 pt-0.5">
              {attachments.slice(requiredDocuments.length).map((att) => (
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
                      className="truncate text-ink/85 underline decoration-dotted hover:text-gold"
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
        </div>
      ) : (
        <>
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
                      className="truncate text-ink/85 underline decoration-dotted hover:text-gold"
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

          <button
            type="button"
            onClick={() => pick()}
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
        </>
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

      {error && <p className="mt-1 text-[11px] text-red-600">{error}</p>}
    </div>
  );
}
