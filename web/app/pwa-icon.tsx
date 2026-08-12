import type { ReactElement } from "react";

/**
 * Layout JSX dùng chung cho mọi icon PWA (favicon, apple-icon, manifest
 * 192/512) — chữ "M" trên nền `--ink`, viền `--gold-soft` — để đổi màu
 * thương hiệu chỉ cần sửa một chỗ.
 */
export function AppIconMark(size: number): ReactElement {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#002d62",
        borderRadius: size * 0.2,
      }}
    >
      <span
        style={{
          fontSize: size * 0.58,
          fontWeight: 700,
          color: "#1a73e8",
          fontFamily: "Georgia, serif",
        }}
      >
        M
      </span>
    </div>
  );
}
