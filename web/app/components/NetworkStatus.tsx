"use client";

import { useEffect, useState } from "react";
import { CloudOff, Wifi } from "lucide-react";

export default function NetworkStatus() {
  const [online, setOnline] = useState(true);
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    setOnline(navigator.onLine);
    const goOffline = () => { setOnline(false); setRestored(false); };
    const goOnline = () => { setOnline(true); setRestored(true); window.setTimeout(() => setRestored(false), 3000); };
    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    return () => { window.removeEventListener("offline", goOffline); window.removeEventListener("online", goOnline); };
  }, []);

  if (online && !restored) return null;
  return <div role="status" aria-live="polite" className={`fixed inset-x-3 top-3 z-[100] mx-auto flex max-w-md items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium text-white shadow-xl ${online ? "bg-emerald-600" : "bg-slate-800"}`}>
    {online ? <Wifi className="h-4 w-4" /> : <CloudOff className="h-4 w-4" />}
    {online ? "Đã kết nối lại" : "Bạn đang ngoại tuyến. Một số dữ liệu có thể chưa cập nhật."}
  </div>;
}
