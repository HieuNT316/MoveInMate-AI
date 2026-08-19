import type { ReactNode } from "react";

const URL_PATTERN = /(https?:\/\/[^\s]+)/g;

/**
 * AI trả lời có thể chứa link thật (vd cổng dịch vụ công) ở dạng chữ thường —
 * tách ra thành `<a>` bấm được, mở tab mới. Chỉ nhận diện `http(s)://...`,
 * không cố đoán domain trần (`example.com`) để tránh bắt nhầm số/ký hiệu.
 *
 * `text.split()` với regex có capture group trả về mảng xen kẽ: chỉ số lẻ
 * luôn là URL đã khớp, chỉ số chẵn là văn bản thường — không cần gọi lại
 * `.test()`/`.exec()` nên tránh hẳn bug `lastIndex` của regex có cờ `g`.
 */
export function linkifyText(text: string): ReactNode[] {
  return text.split(URL_PATTERN).map((part, index) => {
    if (index % 2 === 0) return part;

    // Dấu câu cuối câu (. , ) hay dính liền URL trong văn bản tự nhiên —
    // cắt ra khỏi link để không mở nhầm URL kèm dấu chấm cuối câu.
    const trailingMatch = part.match(/[.,;:)\]]+$/);
    const trailing = trailingMatch ? trailingMatch[0] : "";
    const url = trailing ? part.slice(0, -trailing.length) : part;
    return (
      <span key={index}>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="underline decoration-dotted underline-offset-2 hover:text-gold"
        >
          {url}
        </a>
        {trailing}
      </span>
    );
  });
}
