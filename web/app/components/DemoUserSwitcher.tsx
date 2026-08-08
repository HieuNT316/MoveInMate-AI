"use client";

import { Users } from "lucide-react";

import { useDemoUser } from "../../lib/useDemoUser";

/**
 * ⚠️ TẠM THỜI — chỉ dành cho demo, phải gỡ khi có đăng nhập Supabase thật.
 *
 * Cho phép đổi vai ngay trên màn hình để thấy checklist của chủ hộ và của
 * người thuê khác nhau thế nào — đây là điểm cần chứng minh của sản phẩm.
 */
const DEMO_USERS = [
  { id: 2, label: "Chủ hộ", name: "Trần Văn An" },
  { id: 3, label: "Người thuê", name: "Lê Thị Bình" },
  { id: 1, label: "Ban quản lý", name: "BQL Smart City" },
];

export default function DemoUserSwitcher() {
  const { userId, switchUser, ready } = useDemoUser();

  return (
    <div className="flex items-center gap-2 rounded-full border border-gold/40 bg-gold-tint px-2 py-1.5">
      <Users className="ml-1.5 h-3.5 w-3.5 text-gold" strokeWidth={1.75} />
      <span className="text-[11px] uppercase tracking-wider text-muted">
        Demo
      </span>
      {DEMO_USERS.map((user) => (
        <button
          key={user.id}
          onClick={() => switchUser(user.id)}
          title={user.name}
          className={`rounded-full px-3 py-1 text-xs transition ${
            ready && userId === user.id
              ? "bg-ink font-medium text-white"
              : "text-muted hover:text-ink"
          }`}
        >
          {user.label}
        </button>
      ))}
    </div>
  );
}
