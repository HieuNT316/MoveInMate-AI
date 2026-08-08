"use client";

import { useCallback, useEffect, useState } from "react";

import { DEFAULT_USER_ID, readUserId, writeUserId } from "./api";

/**
 * Danh tính người dùng cho bản demo.
 *
 * ⚠️ TẠM THỜI — thay cho phiên đăng nhập Supabase. Cho phép đổi qua lại giữa
 * chủ hộ và người thuê ngay trên giao diện, để thấy checklist khác nhau thế
 * nào mà không phải đăng xuất đăng nhập lại.
 *
 * `ready` để tránh nhấp nháy: lần render đầu trên server chưa đọc được
 * localStorage nên phải chờ hydrate xong mới gọi API.
 */
export function useDemoUser() {
  const [userId, setUserId] = useState(DEFAULT_USER_ID);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setUserId(readUserId());
    setReady(true);
  }, []);

  const switchUser = useCallback((id: number) => {
    writeUserId(id);
    setUserId(id);
  }, []);

  return { userId, switchUser, ready };
}
