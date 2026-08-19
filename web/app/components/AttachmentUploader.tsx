"use client";

import { useRef, useState } from "react";
import { Check, FileText, Loader2, Paperclip } from "lucide-react";

import { api, ApiError, type Attachment, type DocumentType, type RequiredDocument } from "../../lib/api";

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
 * vì một nút tải chung chung. Mỗi mục có `code` thật (khớp `DocumentType` ở
 * backend) — gửi kèm lúc tải lên (`api.uploadAttachment`) và khớp lại đúng
 * mã đó trong `resolveSlot()`. Tệp tải TRƯỚC khi tính năng này tồn tại không
 * có `document_type` (null) — với hồ sơ như vậy, `resolveSlot` rơi về khớp
 * theo VỊ TRÍ để không hiện sai "chưa tải" cho thứ đã có sẵn.
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
  requiredDocuments?: RequiredDocument[];
  onUploaded: (attachment: Attachment) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  // Slot đang chờ chọn tệp — input file dùng chung cho mọi slot, cần nhớ
  // đang tải CHO mã nào để gắn `document_type` đúng lúc submit.
  const pendingSlotRef = useRef<DocumentType | undefined>(undefined);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pick = (slotCode?: DocumentType) => {
    pendingSlotRef.current = slotCode;
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

  // Tệp tải trước khi có `document_type` (null hết) không khớp theo mã được
  // — rơi về khớp vị trí cho đúng hồ sơ cũ. Có ít nhất 1 tệp mang mã thật thì
  // chuyển hẳn sang khớp theo mã (không trộn hai kiểu nửa vời).
  const codesSupported = attachments.some((a) => a.document_type);

  const resolveSlot = (code: DocumentType, index: number): Attachment | undefined => {
    if (codesSupported) return attachments.find((a) => a.document_type === code);
    return attachments[index];
  };

  return (
    <div className="mt-2">
      {requiredDocuments && requiredDocuments.length > 0 ? (
        <div className="space-y-1">
          <p className="text-[11px] font-medium text-muted">
            Đã tải{" "}
            {
              requiredDocuments.filter((doc, index) => resolveSlot(doc.code, index)).length
            }/{requiredDocuments.length} giấy tờ bắt buộc
          </p>
          <ul className="space-y-1">
            {requiredDocuments.map((doc, index) => {
              const att = resolveSlot(doc.code, index);
              const done = Boolean(att);
              // Chưa khớp theo mã thật được thì vẫn phải ép đúng thứ tự (chỉ
              // mở khoá đúng MỘT slot kế tiếp) để khớp vị trí không sai. Có
              // mã thật rồi thì slot nào thiếu cũng tải được, không cần đúng
              // thứ tự nữa.
              const isNext = !done && (codesSupported || attachments.length === index);
              return (
                <li
                  key={doc.code}
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
                      {doc.label}
                    </a>
                  ) : (
                    <span className="min-w-0 flex-1 truncate">{doc.label}</span>
                  )}

                  {att && (
                    <span className="shrink-0 text-[10px] text-muted">
                      {formatSize(att.size_bytes)}
                    </span>
                  )}

                  {isNext && (
                    <button
                      type="button"
                      onClick={() => pick(doc.code)}
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
