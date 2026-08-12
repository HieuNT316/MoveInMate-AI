"use client";

import { useEffect } from "react";

export default function RegisterServiceWorker() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    // Chỉ bật ở production. Ở dev, SW cache HTML/asset cũ đè lên code vừa
    // sửa — trang trông như "không đổi gì" hoặc lệch hydration giữa bản
    // server mới và HTML cache cũ, dù `npm run dev` đã build đúng.
    if (process.env.NODE_ENV !== "production") {
      // Gỡ SW + xoá cache cũ nếu máy này từng cài ở lần chạy trước — tự dọn,
      // không bắt phải vào DevTools xoá tay.
      navigator.serviceWorker.getRegistrations().then((regs) => {
        regs.forEach((reg) => reg.unregister());
      });
      if ("caches" in window) {
        caches.keys().then((keys) => keys.forEach((key) => caches.delete(key)));
      }
      return;
    }

    navigator.serviceWorker.register("/sw.js").catch((err) => {
      console.error("[sw] đăng ký thất bại:", err);
    });
  }, []);

  return null;
}
