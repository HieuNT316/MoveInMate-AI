"use client";

import { createClient } from "@supabase/supabase-js";

/**
 * Client Supabase phía trình duyệt (US-01).
 *
 * Chỉ dùng ANON key. Service key bỏ qua toàn bộ phân quyền nên tuyệt đối không
 * được xuất hiện ở frontend — nó chỉ nằm ở backend cho việc BQL cấp tài khoản.
 *
 * `persistSession` để phiên sống qua lần tải trang; `autoRefreshToken` để token
 * hết hạn (mặc định 1 giờ) tự được làm mới, nếu không người dùng đang thao tác
 * sẽ đột ngột nhận 401.
 */
const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export const supabaseConfigured = Boolean(url && anonKey);

export const supabase = createClient(url || "http://localhost", anonKey || "public-anon-key", {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
  },
});

/**
 * ⚠️ TẠM THỜI — mật khẩu dùng chung của toàn bộ tài khoản demo, do
 * `scripts/provision_auth.py` đặt. Xoá cùng lúc với `/auth/demo-accounts`.
 * Với cư dân thật, mỗi người có mật khẩu riêng do BQL bàn giao.
 */
export const DEMO_PASSWORD = "MoveInMate!2026";

/** Access token của phiên hiện tại, `null` nếu chưa đăng nhập. */
export async function currentAccessToken(): Promise<string | null> {
  if (!supabaseConfigured) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
