/**
 * US-13 — form nộp hồ sơ theo từng thủ tục.
 *
 * `POST /applications` (docs/CONTRACT_US13.md mục 5) chỉ nhận một trường
 * `note` dạng chuỗi tự do — hợp đồng đã chốt, không đổi được. Form theo từng
 * thủ tục ở đây là lựa chọn riêng của FE: gom các trường có cấu trúc rồi nén
 * thành một đoạn `note` dễ đọc cho BQL, không phải trường riêng ở backend.
 */
export type ApplicationFormField = {
  key: string;
  label: string;
  type: "text" | "number" | "select" | "date";
  placeholder?: string;
  options?: string[];
  required?: boolean;
};

/** Khớp theo `task_name` — đúng tên đã seed ở `scripts/seed_data.py`. Thủ tục
 * không có trong bảng này (vd "Ký nội quy toà nhà") rơi về ô ghi chú tự do. */
const FORM_FIELDS: Record<string, ApplicationFormField[]> = {
  "Đăng ký thẻ xe": [
    {
      key: "vehicle_type",
      label: "Loại xe",
      type: "select",
      options: ["Ô tô", "Xe máy"],
      required: true,
    },
    { key: "plate", label: "Biển số xe", type: "text", placeholder: "Vd. 30A-123.45", required: true },
    { key: "quantity", label: "Số lượng xe cần đăng ký", type: "number", placeholder: "1" },
  ],
  "Đăng ký chỗ đỗ xe cố định": [
    {
      key: "vehicle_type",
      label: "Loại xe",
      type: "select",
      options: ["Ô tô", "Xe máy"],
      required: true,
    },
    { key: "plate", label: "Biển số xe", type: "text", placeholder: "Vd. 30A-123.45", required: true },
  ],
  "Làm thẻ cư dân (chủ hộ)": [
    { key: "card_count", label: "Số lượng thẻ cần làm", type: "number", placeholder: "1", required: true },
  ],
  "Làm thẻ cư dân (người thuê)": [
    { key: "card_count", label: "Số lượng thẻ cần làm", type: "number", placeholder: "1", required: true },
  ],
  "Kích hoạt thẻ bể bơi": [
    { key: "member_count", label: "Số thành viên sử dụng", type: "number", placeholder: "1" },
  ],
  "Kích hoạt thẻ phòng gym": [
    { key: "member_count", label: "Số thành viên sử dụng", type: "number", placeholder: "1" },
  ],
  "Đăng ký thẻ thang máy": [
    { key: "card_count", label: "Số lượng thẻ cần cấp", type: "number", placeholder: "1", required: true },
  ],
  "Đăng ký internet và truyền hình": [
    {
      key: "provider",
      label: "Nhà cung cấp mong muốn",
      type: "select",
      options: ["Viettel", "VNPT", "FPT Telecom"],
      required: true,
    },
    { key: "preferred_date", label: "Ngày mong muốn lắp đặt", type: "date" },
  ],
  "Đăng ký chuyển đồ vào căn hộ": [
    { key: "move_date", label: "Ngày chuyển đồ", type: "date", required: true },
    {
      key: "time_slot",
      label: "Khung giờ",
      type: "select",
      options: ["8:00–10:00", "10:00–12:00", "14:00–16:00", "16:00–18:00"],
      required: true,
    },
    { key: "mover", label: "Đơn vị vận chuyển (nếu có)", type: "text" },
  ],
};

export function getApplicationFormFields(taskName: string): ApplicationFormField[] | null {
  return FORM_FIELDS[taskName] ?? null;
}

/**
 * Thủ tục nào cần ảnh giấy tờ thật để BQL đối chiếu — không phải trang trí,
 * đây là thứ khiến hồ sơ có căn cứ thay vì chỉ là vài dòng chữ tự khai. Chỉ
 * liệt kê thủ tục THẬT SỰ cần giấy tờ; các thủ tục còn lại (kích hoạt tiện
 * ích theo gói đã đăng ký, đặt lịch chuyển đồ...) không cần ảnh vì hệ thống
 * đã có đủ dữ kiện qua hồ sơ cư dân.
 */
const REQUIRED_DOCUMENTS: Record<string, string> = {
  "Làm thẻ cư dân (chủ hộ)": "Ảnh CCCD và giấy tờ chứng minh quyền sở hữu căn hộ",
  "Làm thẻ cư dân (người thuê)": "Ảnh CCCD, hợp đồng thuê nhà và giấy uỷ quyền của chủ hộ",
  "Đăng ký thẻ xe": "Ảnh giấy đăng ký xe (cà vẹt)",
  "Đăng ký chỗ đỗ xe cố định": "Ảnh giấy đăng ký xe (cà vẹt)",
};

export function getRequiredDocument(taskName: string): string | null {
  return REQUIRED_DOCUMENTS[taskName] ?? null;
}

/** Gộp các trường đã điền thành một đoạn text — đây là thứ thật sự gửi vào
 * `note`. Bỏ qua trường trống, giữ nguyên thứ tự khai báo trong form. */
export function composeNote(
  fields: ApplicationFormField[],
  values: Record<string, string>,
  freeNote: string,
): string | undefined {
  const lines = fields
    .map((f) => {
      const v = values[f.key]?.trim();
      return v ? `${f.label}: ${v}` : null;
    })
    .filter((line): line is string => line !== null);

  if (freeNote.trim()) lines.push(freeNote.trim());

  return lines.length > 0 ? lines.join("\n") : undefined;
}
