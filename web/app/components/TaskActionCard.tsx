"use client";

import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import { AlertCircle, Info, Paperclip } from "lucide-react";

export type ActionField = {
  name: string;
  label: string;
  type: "text" | "select" | "date";
  placeholder?: string;
  options?: string[];
  required?: boolean;
  /** Trả về thông báo lỗi, hoặc `null` nếu hợp lệ. Chỉ chạy khi field có giá trị
   * — bắt buộc-hay-không đã tách riêng qua `required`. */
  validate?: (value: string) => string | null;
};

export type TaskActionCardConfig = {
  icon: LucideIcon;
  title: string;
  description: string;
  fields: ActionField[];
  submitLabel: string;
};

/**
 * ⚠️ PROTOTYPE — dựng UI để cả nhóm hình dung "action card", KHÔNG nối submit
 * thật. Bấm nút hành động chỉ validate rồi hiện banner nói rõ đây là bản
 * dựng, không tạo mã hồ sơ hay đổi trạng thái checklist thật — làm giả những
 * thứ đó sẽ vi phạm nguyên tắc "không vẽ số liệu giả" của dự án (CLAUDE.md).
 * Submit thật cần `POST /applications` (Hiếu) + phân loại intent (Hải) —
 * xem contract đề xuất gửi kèm.
 */
export default function TaskActionCard({ config }: { config: TaskActionCardConfig }) {
  const { icon: Icon, title, description, fields, submitLabel } = config;
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [validated, setValidated] = useState(false);

  const setValue = (name: string, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    setValidated(false);
  };

  const handleSubmit = () => {
    const nextErrors: Record<string, string> = {};
    for (const field of fields) {
      const value = (values[field.name] ?? "").trim();
      if (field.required && !value) {
        nextErrors[field.name] = "Bắt buộc nhập";
        continue;
      }
      if (value && field.validate) {
        const message = field.validate(value);
        if (message) nextErrors[field.name] = message;
      }
    }
    setErrors(nextErrors);
    setValidated(Object.keys(nextErrors).length === 0);
  };

  return (
    <div className="w-full max-w-md rounded-2xl border border-gold/40 bg-surface p-5">
      <div className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gold-tint">
          <Icon className="h-4 w-4 text-gold" strokeWidth={1.75} />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">{title}</p>
          <p className="text-[11px] text-muted">{description}</p>
        </div>
      </div>

      <div className="mt-4 space-y-3.5">
        {fields.map((field) => (
          <div key={field.name}>
            <label className="mb-1 block text-xs font-medium text-ink/90">
              {field.label}
              {field.required && <span className="text-gold"> *</span>}
            </label>

            {field.type === "select" ? (
              <select
                value={values[field.name] ?? ""}
                onChange={(event) => setValue(field.name, event.target.value)}
                className={`w-full rounded-lg border bg-background px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-gold/30 ${
                  errors[field.name] ? "border-danger" : "border-border focus:border-gold/50"
                }`}
              >
                <option value="">Chọn...</option>
                {field.options?.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={field.type === "date" ? "date" : "text"}
                value={values[field.name] ?? ""}
                placeholder={field.placeholder}
                onChange={(event) => setValue(field.name, event.target.value)}
                className={`w-full rounded-lg border bg-background px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-gold/30 ${
                  errors[field.name] ? "border-danger" : "border-border focus:border-gold/50"
                }`}
              />
            )}

            {errors[field.name] && (
              <p className="mt-1 flex items-center gap-1 text-[11px] text-danger">
                <AlertCircle className="h-3 w-3 shrink-0" strokeWidth={2} />
                {errors[field.name]}
              </p>
            )}
          </div>
        ))}

        <div>
          <label className="mb-1 block text-xs font-medium text-ink/90">
            Ảnh giấy tờ liên quan
          </label>
          <button
            type="button"
            disabled
            title="Sắp có — chưa nối API tải lên giấy tờ"
            className="flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-lg border border-dashed border-border px-3 py-2.5 text-xs text-muted/60"
          >
            <Paperclip className="h-3.5 w-3.5" strokeWidth={1.75} />
            Sắp có
          </button>
        </div>
      </div>

      <button
        type="button"
        onClick={handleSubmit}
        className="mt-4 w-full rounded-xl bg-ink py-2.5 text-sm font-medium text-white transition hover:bg-ink-soft"
      >
        {submitLabel}
      </button>

      {validated && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-border bg-background px-3 py-2.5">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" strokeWidth={1.75} />
          <p className="text-[11px] leading-relaxed text-muted">
            Dữ liệu hợp lệ. Đây là <span className="font-medium text-ink/85">bản dựng giao diện</span> —
            nút &ldquo;{submitLabel}&rdquo; chưa nối submit thật, không tạo mã hồ sơ hay đổi trạng thái
            checklist. Cần <code className="text-ink/85">POST /applications</code> (Hiếu) + phân loại
            intent (Hải) trước khi lên thật.
          </p>
        </div>
      )}
    </div>
  );
}
