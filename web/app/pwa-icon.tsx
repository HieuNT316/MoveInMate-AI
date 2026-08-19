import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { ReactElement } from "react";

// Đọc một lần lúc build/khởi động route, không phải mỗi request.
const logoDataUri = `data:image/png;base64,${readFileSync(
  join(process.cwd(), "public", "logo-mark.png"),
).toString("base64")}`;

/**
 * Layout JSX dùng chung cho mọi icon PWA (favicon, apple-icon, manifest
 * 192/512) — logo thật từ `public/logo-mark.png` trên nền trắng bo góc —
 * để đổi logo thương hiệu chỉ cần thay một file ảnh.
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
        background: "#ffffff",
        borderRadius: size * 0.2,
      }}
    >
      {/* next/og (satori) render ra ảnh tĩnh, không phải DOM trình duyệt — cần
          <img> thường, next/image không dùng được ở đây. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={logoDataUri}
        alt=""
        width={Math.round(size * 0.88)}
        height={Math.round(size * 0.88)}
      />
    </div>
  );
}
