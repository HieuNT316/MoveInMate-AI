"use client";

import { AlertTriangle, CloudOff } from "lucide-react";

export default function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const offline = typeof navigator !== "undefined" && !navigator.onLine;
  const Icon = offline ? CloudOff : AlertTriangle;
  return <div role="alert" className={`flex flex-col items-center rounded-2xl border px-6 py-10 text-center ${offline ? "border-slate-300 bg-slate-50" : "border-red-200 bg-red-50"}`}><Icon className={`h-6 w-6 ${offline ? "text-slate-600" : "text-red-600"}`} /><h3 className={`mt-3 text-sm font-semibold ${offline ? "text-slate-800" : "text-red-800"}`}>{offline ? "Không có kết nối mạng" : "Không tải được dữ liệu"}</h3><p className={`mt-1 max-w-lg text-sm ${offline ? "text-slate-600" : "text-red-700"}`}>{offline ? "Kiểm tra Wi-Fi hoặc dữ liệu di động rồi thử lại." : message}</p>{onRetry && <button onClick={onRetry} className="mt-4 rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100">Thử lại</button>}</div>;
}
