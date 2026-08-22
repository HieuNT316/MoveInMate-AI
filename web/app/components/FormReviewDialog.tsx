"use client";
import { useRef, useState } from "react";
import { Check, Loader2, Paperclip, ShieldAlert, X } from "lucide-react";
import { api, ApiError, type Application, type ApplicationFormData, type DocumentType, type FormSchema } from "../../lib/api";
import { useToast } from "./Toast";

interface FormReviewDialogProps {
  schema: FormSchema;
  initialData: ApplicationFormData;
  itemName: string;
  userId: number;
  checklistItemId: number;
  onSubmitted: () => void;
  onBack: () => void;
}

const ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf"];
const MAX_BYTES = 5 * 1024 * 1024;

export default function FormReviewDialog({
  schema,
  initialData,
  itemName,
  userId,
  checklistItemId,
  onSubmitted,
  onBack,
}: FormReviewDialogProps) {
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const pendingCodeRef = useRef<DocumentType | undefined>(undefined);

  // Phase 1: form editing
  const [values, setValues] = useState<ApplicationFormData>(
    Object.fromEntries(
      schema.fields.map((f) => [
        f.key,
        initialData[f.key] ?? f.default ?? "",
      ]),
    ),
  );
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Phase 2: attachment upload (after application created)
  const [application, setApplication] = useState<Application | null>(null);
  const [uploadedCodes, setUploadedCodes] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const requiredAttachments = schema.attachments.filter((a) => a.required);
  const allAttachmentsUploaded =
    requiredAttachments.length === 0 ||
    requiredAttachments.every((a) => uploadedCodes.has(a.code));

  const handlePickFile = (code: DocumentType) => {
    pendingCodeRef.current = code;
    inputRef.current?.click();
  };

  const handleFileUpload = async (file: File) => {
    if (!application) return;

    setUploadError(null);
    if (!ALLOWED_TYPES.includes(file.type)) {
      setUploadError("Chỉ nhận ảnh JPG, PNG hoặc file PDF.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setUploadError("Tệp vượt quá 5MB.");
      return;
    }

    const code = pendingCodeRef.current;
    if (!code) return;

    setUploading(true);
    try {
      await api.uploadAttachment(userId, application.application_id, file, code);
      setUploadedCodes((prev) => new Set([...prev, code]));
      toast.show("Đã tải lên giấy tờ");
    } catch (err) {
      if (err instanceof ApiError && err.status === 415) {
        setUploadError("Chỉ nhận ảnh JPG, PNG hoặc file PDF.");
      } else if (err instanceof ApiError && err.status === 413) {
        setUploadError("Tệp quá lớn — giới hạn 5MB.");
      } else {
        setUploadError("Không tải lên được lúc này, thử lại sau.");
      }
      toast.show("Tải giấy tờ không thành công", "error");
    } finally {
      setUploading(false);
    }
  };

  const handleSubmitForm = async () => {
    setSubmitting(true);
    setFormErrors([]);
    try {
      const { currentAccessToken } = await import("../../lib/supabase");
      const token = await currentAccessToken();
      if (!token) throw new Error("No access token");

      const app = await api.submitApplicationWithFormData(
        userId,
        checklistItemId,
        values,
        token,
      );
      setApplication(app);
      toast.show("Đã tạo hồ sơ");
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 422) {
        setFormErrors([error.message || "Thông tin chưa hợp lệ"]);
      } else {
        toast.show("Không tạo được hồ sơ lúc này", "error");
      }
    } finally {
      setSubmitting(false);
    }
  };

  // Phase 2: Attachment upload after application created
  if (application) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-xl">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-lg font-semibold text-ink">
              Tải giấy tờ bổ sung
            </h3>
            <button
              onClick={onSubmitted}
              aria-label="Hoàn tất"
              className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition hover:bg-background hover:text-ink"
            >
              <X className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </div>

          <p className="mt-1 text-sm text-muted">{itemName}</p>

          <div className="mt-3 flex items-start gap-2.5 rounded-xl border border-gold/40 bg-gold-tint px-3.5 py-3 text-xs text-ink/90">
            <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gold" strokeWidth={1.75} />
            <p>
              Hồ sơ đã ghi nhận. Cần tải đủ{" "}
              <span className="font-medium text-ink">
                {requiredAttachments.length} loại giấy tờ
              </span>{" "}
              để Ban quản lý đối chiếu.
            </p>
          </div>

          {/* Attachments list */}
          {schema.attachments.length > 0 && (
            <div className="mt-4 space-y-1.5">
              {schema.attachments.map((att) => {
                const done = uploadedCodes.has(att.code);
                return (
                  <div
                    key={att.code}
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs ${
                      done
                        ? "border-emerald/30 bg-emerald/5 text-ink/85"
                        : "border-border bg-background text-muted"
                    }`}
                  >
                    {done ? (
                      <Check className="h-3.5 w-3.5 shrink-0 text-emerald" strokeWidth={2.5} />
                    ) : (
                      <Paperclip className="h-3.5 w-3.5 shrink-0 text-muted" strokeWidth={2} />
                    )}
                    <span className="min-w-0 flex-1 truncate">
                      {att.label}
                      {att.required && <span className="text-red-500"> *</span>}
                    </span>
                    {done ? (
                      <span className="shrink-0 text-[10px] text-emerald">Đã tải</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handlePickFile(att.code)}
                        disabled={uploading}
                        className="shrink-0 font-medium text-gold transition hover:text-gold-soft disabled:opacity-50"
                      >
                        {uploading ? "..." : "Tải ảnh"}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {uploadError && (
            <p className="mt-2 text-xs text-red-500">{uploadError}</p>
          )}

          <button
            onClick={onSubmitted}
            disabled={!allAttachmentsUploaded}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-medium text-white transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-40"
          >
            {!allAttachmentsUploaded
              ? `Tải ${requiredAttachments.length - uploadedCodes.size} giấy tờ còn thiếu`
              : "Hoàn tất"}
          </button>
          {!allAttachmentsUploaded && (
            <p className="mt-2 text-center text-[11px] text-muted">
              Có thể quay lại bổ sung sau ở trang Việc cần làm.
            </p>
          )}

          <input
            ref={inputRef}
            type="file"
            accept={ALLOWED_TYPES.join(",")}
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) handleFileUpload(file);
            }}
          />
        </div>
      </div>
    );
  }

  // Phase 1: Form fields
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-lg font-semibold text-ink">
            Xem lại thông tin đăng ký
          </h3>
          <button
            onClick={onBack}
            aria-label="Quay lại"
            className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition hover:bg-background hover:text-ink"
          >
            <X className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>

        <p className="mt-1 text-sm text-muted">{itemName}</p>

        {/* Form Fields */}
        <div className="mt-4 space-y-3">
          {schema.fields.map((field) => (
            <label key={field.key} className="block">
              <span className="mb-1.5 block text-xs font-medium text-muted">
                {field.label}
                {field.required && <span className="text-red-600"> *</span>}
              </span>
              {field.type === "select" ? (
                <select
                  value={values[field.key] ?? ""}
                  onChange={(e) =>
                    setValues((v) => ({ ...v, [field.key]: e.target.value }))
                  }
                  className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-ink focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
                >
                  <option value="">— Chọn —</option>
                  {field.options?.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={field.type === "number" ? "number" : "text"}
                  value={values[field.key] ?? ""}
                  onChange={(e) =>
                    setValues((v) => ({ ...v, [field.key]: e.target.value }))
                  }
                  placeholder={field.default}
                  className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-ink focus:border-gold/50 focus:outline-none focus:ring-1 focus:ring-gold/30"
                />
              )}
              {formErrors.some((e) => e.includes(field.label)) && (
                <p className="mt-1 text-xs text-red-500">
                  {formErrors.find((e) => e.includes(field.label))}
                </p>
              )}
            </label>
          ))}
        </div>

        {/* Attachments preview */}
        {schema.attachments.length > 0 && (
          <div className="mt-4 rounded-xl border border-gold/40 bg-gold-tint/30 p-3">
            <p className="text-xs font-medium text-muted">
              Cần kèm {schema.attachments.length} giấy tờ sau:
            </p>
            <ul className="mt-1.5 space-y-0.5">
              {schema.attachments.map((att) => (
                <li key={att.code} className="flex items-center gap-1.5 text-xs text-ink">
                  <Paperclip className="h-3 w-3 shrink-0 text-gold" strokeWidth={2} />
                  <span>
                    {att.label}
                    {att.required && <span className="text-red-500"> *</span>}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* General form errors */}
        {formErrors.length > 0 &&
          !formErrors.some((e) =>
            schema.fields.some((f) => e.includes(f.label)),
          ) && (
            <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {formErrors.join("; ")}
            </p>
          )}

        <div className="mt-5 flex gap-3">
          <button
            onClick={onBack}
            disabled={submitting}
            className="flex-1 rounded-xl border border-border py-3 text-sm font-medium text-ink transition hover:bg-background disabled:opacity-40"
          >
            Quay lại
          </button>
          <button
            onClick={handleSubmitForm}
            disabled={submitting}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-medium text-white transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? "Đang gửi..." : "Tiếp tục"}
          </button>
        </div>
      </div>
    </div>
  );
}
