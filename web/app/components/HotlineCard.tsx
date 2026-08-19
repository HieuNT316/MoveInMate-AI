import { Clock, PhoneCall, ShieldCheck } from "lucide-react";

/**
 * Số liệu Ban quản lý ở đây lấy từ `data/kb/web/vsc-hotline-bql.md` (nguồn
 * công khai, `source_type: unofficial_web`) — CÙNG một tệp mà RAG trích dẫn
 * khi trả lời câu hỏi về hotline. Hard-code ở đây vì chưa có endpoint trả
 * cấu hình liên hệ; đổi số/giờ làm việc thì sửa cả hai chỗ cho khớp.
 */
export const HOTLINE = {
  number: "1900 2323 89",
  note: "Nhấn phím 4 để gặp nhân viên hỗ trợ · 24/7",
  hours: "Văn phòng BQL: 08:00–12:00 và 13:00–17:00",
  source: "Theo trang tham khảo Vinhomes Smart City",
};

/** Dùng chung ở panel chat và Tổng quan. */
export default function HotlineCard() {
  return (
    <div className="rounded-2xl border border-gold/30 bg-gold-tint p-5">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-gold" strokeWidth={1.75} />
        <p className="text-sm font-medium text-ink">Cần hỗ trợ trực tiếp?</p>
      </div>
      <a
        href={`tel:${HOTLINE.number.replace(/\s/g, "")}`}
        className="mt-3 flex items-center gap-2.5 rounded-xl border border-gold/40 bg-surface px-3.5 py-2.5 transition hover:border-gold/70"
      >
        <PhoneCall className="h-4 w-4 shrink-0 text-gold" strokeWidth={1.75} />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">{HOTLINE.number}</p>
          <p className="text-[11px] text-muted">{HOTLINE.note}</p>
        </div>
      </a>
      <p className="mt-2.5 flex items-start gap-1.5 text-[11px] text-muted">
        <Clock className="mt-0.5 h-3 w-3 shrink-0" strokeWidth={1.75} />
        {HOTLINE.hours}
      </p>
      <p className="mt-2 text-[10px] uppercase tracking-wider text-muted/80">{HOTLINE.source}</p>
    </div>
  );
}
