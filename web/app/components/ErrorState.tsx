import { AlertTriangle } from "lucide-react";

export default function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="flex flex-col items-center rounded-2xl border border-red-200 bg-red-50 px-6 py-10 text-center"><AlertTriangle className="h-6 w-6 text-red-600" /><h3 className="mt-3 text-sm font-semibold text-red-800">Không tải được dữ liệu</h3><p className="mt-1 max-w-lg text-sm text-red-700">{message}</p>{onRetry && <button onClick={onRetry} className="mt-4 rounded-lg border border-red-300 bg-white px-4 py-2 text-xs font-medium text-red-700 hover:bg-red-100">Thử lại</button>}</div>;
}
