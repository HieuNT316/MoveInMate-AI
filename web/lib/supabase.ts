/**
 * Supabase client dùng chung cho toàn bộ `web/`.
 *
 * Chỉ dùng để lấy JWT và quản lý phiên đăng nhập (US-01) — backend là
 * FastAPI thuần, không phải Next.js server component, nên không cần
 * `@supabase/ssr`. Xem giải thích đầy đủ ở commit `79caa05`.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Thiếu NEXT_PUBLIC_SUPABASE_URL hoặc NEXT_PUBLIC_SUPABASE_ANON_KEY. " +
      "Điền hai biến này vào web/.env.local (xin Hiếu lấy giá trị từ Supabase dashboard).",
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
