/**
 * Lớp gọi API backend.
 *
 * Kiểu dữ liệu ở đây khớp 1-1 với `src/models/schemas.py`. Đổi contract phía
 * backend thì phải đổi cả file này — xem docs/architecture_diagram.md mục 4.3.
 *
 * Xác thực: JWT của Supabase, gắn ở `authHeaders()` bên dưới. Header `X-User-Id`
 * chỉ còn là lối dự phòng khi chạy local chưa có phiên — backend từ chối hẳn nó
 * khi `APP_ENV=production`.
 */

import { currentAccessToken } from "./supabase";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type OwnershipType = "owner" | "renter";
export type ApartmentType = "studio" | "1pn" | "2pn" | "3pn" | "duplex";
export type ItemType = "bql_actionable" | "third_party_info";
export type DocSourceType =
  | "bql_internal"
  | "public_regulation"
  | "unofficial_web"
  | "synthetic_demo";
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

/** 11 mã cố định — khớp `DocumentType` ở `src/models/schemas.py`. */
export type DocumentType =
  | "cccd"
  | "bien_ban_ban_giao"
  | "hop_dong_thue"
  | "giay_uy_quyen"
  | "dang_ky_xe"
  | "the_cu_dan"
  | "the_xe"
  | "don_dang_ky"
  | "to_khai_ct01"
  | "anh_vneid"
  | "khac";

/** Một loại giấy tờ, kèm nhãn hiển thị — backend trả cả `label` để FE không
 * phải tự giữ bảng nhãn riêng (xem `RequiredDocument` ở schemas.py). */
export type RequiredDocument = {
  code: DocumentType;
  label: string;
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
  /** US-13 — null với `third_party_info` (không có bộ phận BQL nào phụ trách). */
  handling_department: string | null;
  submission_location: string | null;
  processing_time: string | null;
  /** Rỗng = không đòi giấy tờ nào. Nguồn thật duy nhất — KHÔNG tự suy đoán
   * ở FE (đã có một lần lệch dữ liệu thật vì làm vậy, xem lịch sử sửa). */
  required_documents: RequiredDocument[];
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

/**
 * Tín hiệu điều hướng do agent phát ra khi người dùng hỏi CÁCH NỘP hồ sơ
 * (khác với hỏi "cần giấy tờ gì" — câu đó chỉ cần trả lời bằng chữ).
 *
 * `checklist_item_id` là `null` khi backend không đối chiếu được tên thủ tục
 * AI suy ra với đúng một mục trong checklist thật của người dùng. Lúc đó FE
 * **phải ẩn nút**, không điều hướng mù tới chỗ sai.
 */
export type SuggestedAction = {
  type: "navigate_to_submission";
  procedure_name: string;
  checklist_item_id: number | null;
};

export type ChatAnswer = {
  answer: string;
  sources: Source[];
  answer_source: AnswerSource;
  suggested_action?: SuggestedAction | null;
  /** Hội thoại vừa hỏi thuộc về — gửi lại đúng id này ở câu hỏi tiếp theo
   * (`sendChat(userId, message, conversationId)`) để AI hiểu ngữ cảnh. */
  conversation_id: string;
};

/** Một lượt hỏi đáp đã lưu, thuộc về đúng một hội thoại. */
export type ChatHistoryEntry = {
  id: number;
  question: string;
  answer: string;
  answer_source: AnswerSource;
  sources: Source[];
  created_at: string;
};

/** US-07 — một cuộc hội thoại đã lưu, hiển thị trong danh sách để bấm vào
 * xem lại/hỏi tiếp. `preview` là câu hỏi đầu tiên, dùng làm tiêu đề. */
export type ConversationSummary = {
  conversation_id: string;
  preview: string;
  message_count: number;
  last_message_at: string;
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

export type AccountStatus = "active" | "locked";

/** `GET /admin/residents/{id}` — trang toàn cảnh một cư dân (Hiếu, 18/08). */
export type ResidentDetail = {
  profile: Profile;
  checklist: Checklist;
  applications: Application[];
  account_status: AccountStatus;
};

// --- Hồ sơ nộp trực tuyến (US-13) — xem docs/CONTRACT_US13.md ------------

export type ApplicationStatus =
  | "received"
  | "processing"
  | "needs_info"
  | "approved"
  | "delivered"
  | "rejected";

/**
 * `bql_processing` — BQL thật sự xử lý. `self_declared` — thủ tục làm ở cơ
 * quan khác (vd tạm trú), cư dân tự nộp ảnh minh chứng, BQL chỉ ghi nhận.
 * Giao diện KHÔNG được nói "Ban quản lý đang xử lý" với loại sau — mạo nhận
 * quy trình của cơ quan khác.
 */
export type ApplicationKind = "bql_processing" | "self_declared";

export type Attachment = {
  attachment_id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  /** Link đọc tạm thời, hết hạn sau vài phút — không cache, không chia sẻ. */
  url: string | null;
  uploaded_at: string;
  /** Hiếu đã thêm cột thật (migration `4b4ea98a4e85`, 19/08) — null nghĩa là
   * tệp tải lên trước khi có tính năng này, hoặc BQL chưa gán loại. */
  document_type?: DocumentType | null;
};

export type EmbedStatus = "pending" | "processing" | "ready" | "failed";

export type AdminDocument = {
  document_id: number;
  title: string;
  file_path: string;
  embed_status: EmbedStatus;
  uploaded_at: string;
};

export type Application = {
  application_id: number;
  checklist_item_id: number;
  task_name: string;
  status: ApplicationStatus;
  kind: ApplicationKind;
  attachments: Attachment[];
  /** `null` = còn tệp chưa phân loại nên backend chưa thể kết luận thiếu gì. */
  missing_documents?: RequiredDocument[] | null;
  unlabelled_count?: number;
  handling_department: string | null;
  submission_location: string | null;
  processing_time: string | null;
  note: string | null;
  bql_note: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminApplication = Application & {
  user_id: number;
  full_name: string;
  apartment: string;
};

// --- AI Form Generation (Task 6) -----------------------------------

export type FormField = {
  key: string;
  label: string;
  type: "text" | "number" | "select" | "date";
  options?: string[];
  required: boolean;
  question?: string;
  pattern?: string;
  default?: string;
};

export type AttachmentSpec = {
  code: string;
  label: string;
  required: boolean;
};

export type FormSchema = {
  fields: FormField[];
  attachments: AttachmentSpec[];
};

export type ApplicationFormData = Record<string, string>;

export type CreateApplicationPayload = {
  checklist_item_id: number;
  note?: string;
};

export type UpdateApplicationStatusPayload = {
  status: ApplicationStatus;
  bql_note?: string;
};

export type CreateUserPayload = {
  full_name: string;
  email: string;
  apartment: string;
  building: string;
};

/**
 * Mật khẩu tạm chỉ xuất hiện đúng một lần ở đây — backend không lưu lại,
 * không có cách xem lại. BQL phải chép ngay để bàn giao cho cư dân.
 */
export type CreatedUser = Profile & { temporary_password: string };

/**
 * ⚠️ TẠM THỜI — tài khoản mẫu cho màn đăng nhập demo.
 * Xoá cùng lúc với `/auth/demo-accounts` khi có Supabase Auth.
 */
export type DemoAccount = {
  user_id: number;
  full_name: string;
  email: string;
  role: "resident" | "admin";
  /** Mô tả hồ sơ, vd "Chủ hộ · 2PN · có ô tô · pool, gym". */
  summary: string;
  /** Số mục rule engine sinh ra cho hồ sơ này — khác nhau giữa các persona. */
  checklist_total: number;
};

/**
 * Đích tới sau khi đăng nhập/đổi persona — dùng chung giữa `login/page.tsx`
 * và `DemoUserSwitcher`. BQL luôn vào `/bql`, kể cả khi `onboarding_completed_at`
 * null (BQL không có checklist nên trường này vốn không áp dụng, không phải
 * dấu hiệu "chưa hoàn tất" như với cư dân).
 */
export function destinationFor(profile: Profile): string {
  if (profile.role === "admin") return "/bql/dashboard";
  return profile.onboarding_completed_at ? "/dashboard" : "/onboarding";
}

export const CHAT_AUTO_OPEN_KEY = "moveinmate.chat-auto-opened";

/**
 * Gọi ngay sau khi đăng nhập/đổi persona thành công (trước `router.push`) —
 * xoá cờ "đã tự bung AI Chat" để mỗi lần đăng nhập đều thấy bong bóng chat tự
 * bung ra ở /dashboard, không chỉ đúng một lần cho cả tuổi thọ của tab.
 */
export function resetChatAutoOpen(): void {
  sessionStorage.removeItem(CHAT_AUTO_OPEN_KEY);
}

const STORAGE_KEY = "moveinmate.demo-user-id";

/**
 * `null` = chưa đăng nhập. KHÔNG có id mặc định: đoán một id rồi gọi API là
 * cách chắc chắn nhận 401 khi dữ liệu được seed lại và id đổi.
 */
export function readUserId(): number | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  const parsed = raw ? Number(raw) : NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function clearUserId(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}

export function writeUserId(id: number): void {
  window.localStorage.setItem(STORAGE_KEY, String(id));
}

/**
 * Ưu tiên JWT của Supabase; chưa có phiên thì rơi về `X-User-Id` để bộ đổi
 * persona trong bản demo còn chạy. Backend cũng ưu tiên JWT và chặn hẳn header
 * này ở production, nên đây chỉ là lối dev, không phải cửa sau.
 */
async function authHeaders(userId: number): Promise<HeadersInit> {
  const token = await currentAccessToken();
  return token
    ? { Authorization: `Bearer ${token}` }
    : { "X-User-Id": String(userId) };
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
 * Phân biệt "backend không chạy / không nối được mạng" (fetch tự throw) với
 * "backend có phản hồi nhưng trả lỗi" (ApiError, ví dụ 401/404/500) — hai
 * tình huống khác nhau, gộp chung một câu dễ chẩn đoán sai nguyên nhân.
 */
export function describeError(err: unknown): string {
  console.error("[api] request thất bại:", err);
  if (err instanceof ApiError) {
    return `Backend trả lỗi ${err.status}: ${err.message || "không rõ chi tiết"}`;
  }
  return "Không kết nối được backend. Kiểm tra đã chạy `uvicorn src.main:app --reload` chưa.";
}

/**
 * FastAPI trả lỗi dạng `{"detail": "..."}` — lấy đúng field đó thay vì hiện
 * cả JSON thô lên UI. Không phải mọi lỗi đều có dạng này (vd lỗi hạ tầng
 * không qua FastAPI), nên rơi về text gốc khi parse thất bại.
 */
function parseErrorDetail(rawText: string, statusText: string): string {
  if (!rawText) return statusText;
  try {
    const parsed = JSON.parse(rawText);
    if (typeof parsed?.detail === "string") return parsed.detail;
  } catch {
    // Không phải JSON — dùng nguyên text.
  }
  return rawText;
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
    throw new ApiError(response.status, parseErrorDetail(detail, response.statusText));
  }
  return response.json() as Promise<T>;
}

/**
 * Như `request`, nhưng KHÔNG set `Content-Type` cứng — để trình duyệt tự
 * gắn boundary của `multipart/form-data` khi `body` là `FormData`. Set tay
 * `Content-Type: multipart/form-data` sẽ thiếu boundary, backend không parse
 * được. Chỉ dùng cho upload tệp (`POST /applications/{id}/attachments`).
 */
async function requestMultipart<T>(
  path: string,
  userId: number,
  body: FormData,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: await authHeaders(userId),
    body,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, parseErrorDetail(detail, response.statusText));
  }
  return response.json() as Promise<T>;
}

/** Gọi endpoint không cần danh tính — chỉ dùng cho luồng đăng nhập. */
async function publicRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, parseErrorDetail(detail, response.statusText));
  }
  return response.json() as Promise<T>;
}

export const api = {
  /** ⚠️ TẠM THỜI — persona mẫu để demo nhanh. */
  getDemoAccounts: () => publicRequest<DemoAccount[]>("/auth/demo-accounts"),

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

  /** Bỏ trống `conversationId` để bắt đầu hội thoại mới; truyền lại giá trị
   * từ `ChatAnswer.conversation_id` trước đó để AI hiểu ngữ cảnh câu hỏi
   * tiếp nối (vd "còn phí thì sao?"). */
  sendChat: (userId: number, message: string, conversationId?: string) =>
    request<ChatAnswer>("/chat", userId, {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: conversationId ?? null }),
    }),

  /** US-07 — danh sách hội thoại đã lưu. Backend lọc theo `user_id` xác
   * thực, không theo tham số nào FE gửi lên — mỗi người chỉ nhận được đúng
   * hội thoại của chính mình dù có cố ý truyền `userId` của người khác. */
  getConversations: (userId: number) =>
    request<ConversationSummary[]>("/chat/conversations", userId),

  /** Toàn bộ tin nhắn của MỘT hội thoại — để mở lại và hỏi tiếp. Backend
   * kiểm tra sở hữu qua cả `user_id` lẫn `conversationId`, trả 404 nếu
   * không phải hội thoại của người gọi (không phân biệt "không tồn tại" với
   * "không phải của bạn" để không lộ UUID nào có thật). */
  getConversationMessages: (userId: number, conversationId: string) =>
    request<ChatHistoryEntry[]>(`/chat/conversations/${conversationId}/messages`, userId),

  getDashboard: (userId: number) =>
    request<Dashboard>("/admin/dashboard", userId),

  createResident: (userId: number, payload: CreateUserPayload) =>
    request<CreatedUser>("/admin/users", userId, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /** Toàn cảnh một cư dân — hồ sơ, checklist, đơn đã nộp, trạng thái tài
   * khoản trong một lần gọi. 404 nếu id không tồn tại hoặc không phải
   * cư dân (kể cả khi trỏ vào tài khoản admin — backend cố tình chặn). */
  getResidentDetail: (userId: number, targetUserId: number) =>
    request<ResidentDetail>(`/admin/residents/${targetUserId}`, userId),

  /** Khoá/mở tài khoản. 403 nếu người gọi không phải admin, 404 như trên. */
  updateAccountStatus: (userId: number, targetUserId: number, status: AccountStatus) =>
    request<ResidentDetail>(`/admin/residents/${targetUserId}/status`, userId, {
      method: "PATCH",
      body: JSON.stringify({ account_status: status }),
    }),

  /** Sinh mật khẩu tạm mới — chỉ hiện đúng một lần trong response, không
   * lưu lại được. 409 nếu cư dân chưa từng được cấp tài khoản đăng nhập. */
  resetResidentPassword: (userId: number, targetUserId: number) =>
    request<{ temporary_password: string }>(
      `/admin/residents/${targetUserId}/reset-password`,
      userId,
      { method: "POST" },
    ),

  /** US-13 — nộp hồ sơ cho một mục checklist. 409 nếu mục đó đã có hồ sơ
   * đang mở, 404 nếu mục không thuộc checklist của chính người gọi. */
  createApplication: (userId: number, payload: CreateApplicationPayload) =>
    request<Application>("/applications", userId, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /** AI Form Generation (Task 6) — lấy schema form từ backend. */
  getFormSchema: (itemId: number, token: string) =>
    request<FormSchema | null>(`/checklist/${itemId}/form-schema`, itemId, {
      headers: { Authorization: `Bearer ${token}` },
    }),

  /** AI Form Generation (Task 6) — nộp hồ sơ kèm form_data. */
  submitApplicationWithFormData: (
    userId: number,
    itemId: number,
    formData: ApplicationFormData,
    token: string,
  ) =>
    request<Application>("/applications", userId, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ checklist_item_id: itemId, form_data: formData }),
    }),

  /** Hồ sơ của chính cư dân đang đăng nhập, mới nhất trước. */
  getApplications: (userId: number) =>
    request<Application[]>("/applications", userId),

  /** US-13 mục 7 — tải một tệp minh chứng (CCCD, VNeID...) lên cho một hồ sơ
   * đã nộp. Giới hạn 5MB, chỉ nhận jpg/png/pdf — backend chặn lại (415/413)
   * dù FE có kiểm tay trước để phản hồi nhanh hơn.
   *
   * `documentType` — gắn tệp với đúng loại giấy tờ trong `required_documents`
   * của mục checklist (route thật, Hiếu 19/08). Optional: để trống thì tệp
   * ở trạng thái "chưa phân loại", không phải lỗi. */
  uploadAttachment: (
    userId: number,
    applicationId: number,
    file: File,
    documentType?: DocumentType,
  ) => {
    const form = new FormData();
    form.append("file", file);
    if (documentType) form.append("document_type", documentType);
    return requestMultipart<Attachment>(
      `/applications/${applicationId}/attachments`,
      userId,
      form,
    );
  },

  /** URL ký chỉ được lấy khi người dùng bấm mở; không gọi trước cho danh sách. */
  getAttachmentUrl: (userId: number, applicationId: number, attachmentId: number) =>
    request<{ url: string }>(
      `/applications/${applicationId}/attachments/${attachmentId}/url`,
      userId,
    ),

  /** BQL xem hồ sơ của mọi cư dân. `status`/`department` là bộ lọc tuỳ chọn
   * — bỏ trống để lấy tất cả. Yêu cầu role admin, backend tự chặn 403. */
  getAdminApplications: (
    userId: number,
    filter?: { status?: ApplicationStatus; department?: string },
  ) => {
    const params = new URLSearchParams();
    if (filter?.status) params.set("status", filter.status);
    if (filter?.department) params.set("department", filter.department);
    const qs = params.toString();
    return request<AdminApplication[]>(`/admin/applications${qs ? `?${qs}` : ""}`, userId);
  },

  /** US-13 — BQL đổi trạng thái một hồ sơ. Backend không ép thứ tự chuyển
   * trạng thái (có thể quay lại `needs_info` sau khi đã `approved`), và chặn
   * 409 nếu duyệt hồ sơ `self_declared` chưa có ảnh minh chứng nào. */
  updateApplicationStatus: (
    userId: number,
    applicationId: number,
    payload: UpdateApplicationStatusPayload,
  ) =>
    request<Application>(`/admin/applications/${applicationId}`, userId, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  getAdminDocuments: (userId: number) =>
    request<AdminDocument[]>("/admin/documents", userId),

  createAdminDocument: (userId: number, payload: { title: string; content: string }) =>
    request<AdminDocument>("/admin/documents", userId, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
