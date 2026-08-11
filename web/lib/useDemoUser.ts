"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { readUserId, writeUserId } from "./api";

/**
 * Danh tính người dùng cho bản demo.
 *
 * ⚠️ TẠM THỜI — thay cho phiên đăng nhập Supabase.
 *
 * KHÔNG có id mặc định. Trước đây hook này trả sẵn một id cứng, nên trình duyệt
 * chưa từng đăng nhập vẫn gọi API bằng id đó; trên SQLite thì tình cờ đúng, còn
 * trên Supabase sequence đã chạy lên nên id đó không tồn tại và mọi trang chết
 * bằng 401. Chưa đăng nhập thì đẩy thẳng về `/login`.
 *
 * `ready` chỉ bật khi đã có id thật. Trang nào gọi API cũng phải chờ `ready`,
 * nếu không sẽ bắn request bằng id rỗng trong lúc chờ chuyển hướng.
 */
export function useDemoUser() {
  const router = useRouter();
  const [userId, setUserId] = useState(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = readUserId();
    if (stored === null) {
      router.replace("/login");
      return;
    }
    setUserId(stored);
    setReady(true);
  }, [router]);

  const switchUser = useCallback((id: number) => {
    writeUserId(id);
    setUserId(id);
    setReady(true);
  }, []);

  return { userId, switchUser, ready };
}
