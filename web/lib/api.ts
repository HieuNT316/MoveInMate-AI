/**
 * Lớp gọi API backend.
 *
 * Kiểu dữ liệu ở đây khớp 1-1 với `src/models/schemas.py`. Đổi contract phía
 * backend thì phải đổi cả file này — xem docs/architecture_diagram.md mục 4.3.
 *
 * ⚠️ Xác thực hiện vẫn ĐANG CHUYỂN TIẾP: `src/api/deps.py` (Hiếu) hiện chỉ
 * đọc header `X-User-Id`, chưa verify JWT — nên vẫn phải gửi header đó để
 * không phá API đang chạy. Đã gắn thêm `Authorization: Bearer <jwt>` thật từ
 * Supabase song song — vô hại với backend hiện tại (bị bỏ qua), và backend
 * chỉ cần bật verify JWT (không cần đổi gì phía FE) là chuyển hẳn sang dùng
 * header này thay X-User-Id.
 */

import { getAccessToken } from "./session";

// `||` (không phải `??`) — .env.local để trống ("") vẫn phải fallback, vì
// `??` chỉ coi null/undefined là "chưa có giá trị", không coi chuỗi rỗng
// là như vậy. Thiếu chỗ này từng khiến API_BASE = "" và mọi request gọi
// nhầm vào chính Next.js (đường dẫn tương đối) thay vì backend FastAPI.
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export type OwnershipType = "owner" | "renter";
export type ApartmentType = "studio" | "1pn" | "2pn" | "3pn" | "duplex";
export type ItemType = "bql_actionable" | "third_party_info";
export type DocSourceType = "bql_internal" | "public_regulation";
export type AnswerSource = "faq" | "rag" | "no_context";
export type AmenityPackage = "pool" | "gym" | "tennis" | "bbq" | "kids_area";

export type Profile = {
  user_id: number;
  full_name: string;
  email: string;
  apartment: string;
  building: string;
  role: "resident" | "admin";
  ownership_type: OwnershipType | null;
  apartment_type: ApartmentType | null;
  has_car: boolean | null;
  amenity_packages: AmenityPackage[];
  onboarding_completed_at: string | null;
};

export type ChecklistItem = {
  id: number;
  task_name: string;
  description: string;
  category: string;
  item_type: ItemType;
  order_index: number;
  completed: boolean;
  completed_at: string | null;
};

export type ProgressSummary = {
  total: number;
  completed: number;
  percent: number;
};

export type Checklist = {
  items: ChecklistItem[];
  /** Cư dân xem — gồm cả thủ tục ở cơ quan bên ngoài. */
  overall: ProgressSummary;
  /** BQL xem — chỉ thủ tục BQL xử lý được. */
  bql_scope: ProgressSummary;
  onboarding_completed: boolean;
};

export type Source = {
  document_id: number;
  title: string;
  snippet: string;
  source_type: DocSourceType;
};

export type ChatAnswer = {
  answer: string;
  sources: Source[];
  answer_source: AnswerSource;
};

export type OnboardingPayload = {
  ownership_type: OwnershipType;
  apartment_type: ApartmentType;
  has_car: boolean;
  amenity_packages: AmenityPackage[];
};

/** PATCH — chỉ gửi field muốn đổi. */
export type ProfilePatch = Partial<OnboardingPayload>;

export type ResidentProgress = {
  user_id: number;
  full_name: string;
  apartment: string;
  ownership_type: OwnershipType | null;
  onboarded: boolean;
  bql_scope: ProgressSummary;
};

export type Dashboard = {
  residents: ResidentProgress[];
  total_residents: number;
};

const STORAGE_KEY = "moveinmate.demo-user-id";
export const DEFAULT_USER_ID = 2;

export function readUserId(): number {
  if (typeof window === "undefined") return DEFAULT_USER_ID;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  const parsed = raw ? Number(raw) : NaN;
  return Number.isFinite(parsed) ? parsed : DEFAULT_USER_ID;
}

export function writeUserId(id: number): void {
  window.localStorage.setItem(STORAGE_KEY, String(id));
}

async function authHeaders(userId: number): Promise<HeadersInit> {
  const headers: Record<string, string> = { "X-User-Id": String(userId) };
  const token = await getAccessToken().catch(() => null);
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

/**
 * Phân biệt "backend không chạy/không nối được mạng" (fetch tự throw) với
 * "backend có phản hồi nhưng trả lỗi" (ApiError, ví dụ 401/404/500) — hai
 * tình huống khác nhau, gộp chung một câu dễ chẩn đoán sai nguyên nhân.
 */
export function describeError(err: unknown): string {
  console.error("[api] request thất bại:", err);
  if (err instanceof ApiError) {
    return `Backend trả lỗi ${err.status}: ${err.message || "không rõ chi tiết"}`;
  }
  return "Không kết nối được backend. Kiểm tra đã chạy `uvicorn src.main:app --reload` ở thư mục gốc repo (không phải trong web/) chưa.";
}

async function request<T>(
  path: string,
  userId: number,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(await authHeaders(userId)),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getProfile: (userId: number) => request<Profile>("/profile", userId),

  submitOnboarding: (userId: number, payload: OnboardingPayload) =>
    request<Profile>("/onboarding", userId, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateProfile: (userId: number, patch: ProfilePatch) =>
    request<Profile>("/profile", userId, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  getChecklist: (userId: number) => request<Checklist>("/checklist", userId),

  setChecklistItem: (userId: number, itemId: number, completed: boolean) =>
    request<Checklist>(`/checklist/${itemId}`, userId, {
      method: "PATCH",
      body: JSON.stringify({ completed }),
    }),

  sendChat: (userId: number, message: string) =>
    request<ChatAnswer>("/chat", userId, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  getDashboard: (userId: number) =>
    request<Dashboard>("/admin/dashboard", userId),
};
