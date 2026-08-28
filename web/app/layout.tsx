import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import RegisterServiceWorker from "./register-service-worker";
import { ToastProvider } from "./components/Toast";
import NetworkStatus from "./components/NetworkStatus";

// Chỉ dùng một font (Inter, có subset "vietnamese" cho dấu tiếng Việt).
// Trước đây có thêm Playfair Display (serif) cho heading/số liệu, nhưng
// nét serif cong khiến chữ trông "quăn" và số trông "nùn nùn" ở size lớn
// — bỏ hẳn, `.font-display`/`font-serif` trong globals.css giờ trỏ về
// cùng font Inter này (xem --font-display trong globals.css).
const body = Inter({
  variable: "--font-body",
  subsets: ["latin", "vietnamese"],
});

export const metadata: Metadata = {
  title: "MoveInMate AI | Trợ lý bàn giao nhà cao cấp",
  description: "Nền tảng AI hỗ trợ cư dân nhận nhà chuyên nghiệp, chỉn chu và đẳng cấp.",
};

export const viewport: Viewport = {
  themeColor: "#002d62",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className={body.variable}>
      <body>
        <ToastProvider>
          {children}
          <NetworkStatus />
          <RegisterServiceWorker />
        </ToastProvider>
      </body>
    </html>
  );
}
