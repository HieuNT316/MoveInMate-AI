/**
 * Helper đọc/theo dõi phiên đăng nhập Supabase.
 *
 * Supabase JS tự lưu session vào localStorage và tự refresh token — ở đây
 * chỉ bọc lại vài hàm hay dùng, không tự quản lý storage.
 */

import type { Session } from "@supabase/supabase-js";

import { supabase } from "./supabase";

export async function getSession(): Promise<Session | null> {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  return data.session;
}

export async function signInWithPassword(
  email: string,
  password: string,
): Promise<Session> {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });
  if (error) throw error;
  if (!data.session) throw new Error("Đăng nhập thất bại, không có phiên trả về.");
  return data.session;
}

export async function getAccessToken(): Promise<string | null> {
  const session = await getSession();
  return session?.access_token ?? null;
}

export function subscribeToAuthChanges(
  callback: (session: Session | null) => void,
): () => void {
  const {
    data: { subscription },
  } = supabase.auth.onAuthStateChange((_event, session) => {
    callback(session);
  });
  return () => subscription.unsubscribe();
}

export async function signOut(): Promise<void> {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}
