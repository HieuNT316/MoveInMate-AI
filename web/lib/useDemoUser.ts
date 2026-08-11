"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { readUserId, writeUserId } from "./api";

/**
 * Người dùng nào đang đăng nhập, theo góc nhìn của UI.
 *
 * Phiên thật nằm ở Supabase; hook này chỉ giữ `user_id` của hồ sơ cư dân để bộ
 * đổi persona biết đang tô đậm nút nào. Mọi request đi kèm Bearer token, không
 * kèm id này.
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
