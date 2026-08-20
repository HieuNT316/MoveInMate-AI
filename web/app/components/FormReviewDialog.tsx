"use client";
import { useState } from "react";
import { Loader2, X } from "lucide-react";
import type { FormSchema, ApplicationFormData } from "../../lib/api";

interface FormReviewDialogProps {
  schema: FormSchema;
  initialData: ApplicationFormData;
  itemName: string;
  onConfirm: (data: ApplicationFormData) => Promise<void>;
  onBack: () => void;
}

export default function FormReviewDialog({
  schema,
  initialData,
  itemName,
  onConfirm,
  onBack,
}: FormReviewDialogProps) {
  const [values, setValues] = useState<ApplicationFormData>(
    Object.fromEntries(
      schema.fields.map((f) => [
        f.key,
        initialData[f.key] ?? f.default ?? "",
      ]),
    ),
  );
  const [errors, setErrors] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    setErrors([]);
    try {
      await onConfirm(values);
    } catch (e: any) {
      if (e?.status === 422) {
        const detail = e?.data?.detail;
        setErrors(Array.isArray(detail) ? detail : [detail ?? "Lỗi xác thực"]);
      }
    } finally {
      setSubmitting(false);
    }
  };

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
              {errors.some((e) => e.includes(field.label)) && (
                <p className="mt-1 text-xs text-red-500">
                  {errors.find((e) => e.includes(field.label))}
                </p>
              )}
            </label>
          ))}
        </div>

        {errors.length > 0 && !errors.some((e) => schema.fields.some((f) => e.includes(f.label))) && (
          <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errors.join("; ")}
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
            onClick={handleSubmit}
            disabled={submitting}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-medium text-white transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? "Đang gửi..." : "Gửi hồ sơ"}
          </button>
        </div>
      </div>
    </div>
  );
}
