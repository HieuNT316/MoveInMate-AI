"use client";

import { Bot, Car, KeyRound, MapPin } from "lucide-react";

import TaskActionCard, { type TaskActionCardConfig } from "../../components/TaskActionCard";

/**
 * ⚠️ PROTOTYPE nội bộ — không link trong nav, không cần đăng nhập, không gọi
 * API thật. Dựng để cả nhóm xem hình hài "action card" trong AI Chat trước
 * khi chốt contract với Hiếu (BE, endpoint submit) và Hải (AI, phân loại
 * intent) — xem PROJECT_CHARTER.md mục 12 (Governance).
 *
 * 3 thủ tục ưu tiên theo tần suất — nhóm "chủ hộ + xe" đang đông nhất trong
 * demo data nên thẻ xe xếp trước.
 */
const MOCK_TASKS: {
  question: string;
  config: TaskActionCardConfig;
}[] = [
  {
    question: "Tôi muốn đăng ký thẻ xe ô tô",
    config: {
      icon: Car,
      title: "Đăng ký thẻ xe",
      description: "Điền thông tin xe để Ban quản lý cấp thẻ ra/vào",
      submitLabel: "Gửi hồ sơ",
      fields: [
        {
          name: "vehicle_type",
          label: "Loại xe",
          type: "select",
          options: ["Ô tô", "Xe máy"],
          required: true,
        },
        {
          name: "plate_number",
          label: "Biển số xe",
          type: "text",
          placeholder: "vd 30A-123.45",
          required: true,
          validate: (value) =>
            /^[0-9]{2}[A-Z]?-?[0-9]{3,5}(\.[0-9]{2})?$/i.test(value)
              ? null
              : "Biển số chưa đúng định dạng",
        },
        {
          name: "chassis_number",
          label: "Số khung / số máy",
          type: "text",
          placeholder: "Theo đăng ký xe",
          required: true,
        },
      ],
    },
  },
  {
    question: "Đăng ký tạm trú thế nào?",
    config: {
      icon: MapPin,
      title: "Khai báo tạm trú",
      description: "Ngoài phạm vi BQL — chuyển tới công an phường, chỉ hỗ trợ điền trước thông tin",
      submitLabel: "Xác nhận khai báo",
      fields: [
        {
          name: "full_name",
          label: "Họ tên người tạm trú",
          type: "text",
          required: true,
        },
        {
          name: "id_number",
          label: "Số CCCD",
          type: "text",
          required: true,
          validate: (value) => (/^\d{12}$/.test(value) ? null : "CCCD phải gồm 12 chữ số"),
        },
        {
          name: "relation",
          label: "Quan hệ với chủ hộ",
          type: "select",
          options: ["Người thuê", "Người thân", "Khác"],
          required: true,
        },
        {
          name: "expected_from",
          label: "Ngày dự kiến bắt đầu lưu trú",
          type: "date",
          required: true,
        },
      ],
    },
  },
  {
    question: "Đặt lịch nhận chìa khóa căn hộ",
    config: {
      icon: KeyRound,
      title: "Đặt lịch nhận chìa khóa",
      description: "Chọn thời điểm tới văn phòng BQL để nhận bàn giao",
      submitLabel: "Xác nhận đặt lịch",
      fields: [
        {
          name: "date",
          label: "Ngày mong muốn",
          type: "date",
          required: true,
        },
        {
          name: "slot",
          label: "Khung giờ",
          type: "select",
          options: ["08:00–10:00", "10:00–12:00", "13:00–15:00", "15:00–17:00"],
          required: true,
        },
      ],
    },
  },
];

export default function ActionCardPrototypePage() {
  return (
    <div className="min-h-screen bg-background px-6 py-10">
      <div className="mx-auto max-w-2xl">
        <div className="rounded-2xl border border-gold/40 bg-gold-tint px-5 py-4">
          <p className="text-sm font-semibold text-ink">
            ⚠️ Prototype nội bộ — không phải màn hình thật
          </p>
          <p className="mt-1 text-xs leading-relaxed text-ink/70">
            Dựng UI &ldquo;action card&rdquo; trong bubble AI Chat để cả nhóm hình dung trước khi
            chốt contract. Nút hành động chỉ validate input — bấm xong{" "}
            <strong>không</strong> tạo mã hồ sơ, không đổi checklist thật. Câu hỏi người dùng ở mỗi
            khối là giả lập, không gọi `/chat` thật.
          </p>
        </div>

        <div className="mt-8 space-y-8">
          {MOCK_TASKS.map(({ question, config }) => (
            <div key={config.title}>
              <div className="flex justify-end">
                <div className="max-w-lg rounded-2xl rounded-br-sm bg-ink px-5 py-3.5 text-[13.5px] text-white">
                  {question}
                </div>
              </div>

              <div className="mt-3 flex justify-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink">
                  <Bot className="h-5 w-5 text-gold-soft" strokeWidth={1.75} />
                </div>
                <TaskActionCard config={config} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
