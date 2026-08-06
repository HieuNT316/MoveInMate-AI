"use client";

import { useState } from "react";
import Layout from "../components/Layout";
import { Check } from "lucide-react";

export default function ChecklistPage() {
  const [steps, setSteps] = useState([
    { id: 1, title: "Ký biên bản bàn giao", done: true },
    { id: 2, title: "Đăng ký cư dân", done: true },
    { id: 3, title: "Đăng ký gửi xe", done: false },
    { id: 4, title: "Nhận thẻ cư dân", done: false },
    { id: 5, title: "Lắp đặt nội thất", done: false },
    { id: 6, title: "Hoàn tất hồ sơ", done: false },
  ]);

  const toggleStep = (id: number) => {
    setSteps(
      steps.map((step) =>
        step.id === id ? { ...step, done: !step.done } : step
      )
    );
  };

  const completed = steps.filter((step) => step.done).length;
  const percent = Math.round((completed / steps.length) * 100);

  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        {/* Summary */}
        <div className="rounded-2xl border border-border bg-surface p-8">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-xl font-semibold text-ink">
              Tiến độ nhận nhà
            </h2>
            <span className="font-display text-2xl font-semibold text-emerald">
              {percent}%
            </span>
          </div>

          <div className="mt-5 h-3 w-full rounded-full bg-border">
            <div
              className="h-3 rounded-full bg-gradient-to-r from-gold to-gold-soft transition-all"
              style={{ width: `${percent}%` }}
            />
          </div>

          <p className="mt-4 text-sm text-muted">
            Bạn đã hoàn thành {completed}/{steps.length} thủ tục nhận nhà.
          </p>
        </div>

        {/* Checklist timeline */}
        <div className="mt-8 rounded-2xl border border-border bg-surface p-8">
          <h2 className="font-display mb-6 text-xl font-semibold text-ink">
            Các mốc bàn giao
          </h2>

          <ol className="space-y-0">
            {steps.map((step, i) => (
              <li key={step.id} className="relative flex gap-4 pb-6 last:pb-0">
                {i !== steps.length - 1 && (
                  <span
                    className={`absolute left-[11px] top-7 h-[calc(100%-1.75rem)] w-px ${
                      step.done ? "bg-emerald/40" : "bg-border"
                    }`}
                  />
                )}

                <button
                  onClick={() => toggleStep(step.id)}
                  aria-label={step.title}
                  className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition ${
                    step.done
                      ? "border-emerald bg-emerald text-white"
                      : "border-border text-transparent hover:border-gold/50"
                  }`}
                >
                  <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                </button>

                <button
                  onClick={() => toggleStep(step.id)}
                  className="flex-1 rounded-lg px-1 py-0.5 text-left text-sm transition hover:text-gold"
                >
                  <span className={step.done ? "text-ink" : "text-muted"}>
                    {step.title}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </Layout>
  );
}
