// Sinh service worker tại build time thay vì file tĩnh trong `public/`, để
// CACHE_NAME đổi theo mỗi lần deploy (mã commit Vercel, hoặc mốc build lúc
// `next build` chạy nếu không có mã commit — ví dụ chạy local).
// Trước đây CACHE_NAME cố định "moveinmate-shell-v1" nên ai đã từng mở trang
// sẽ tiếp tục thấy bản cũ sau mọi lần deploy, kể cả Ctrl+F5, vì service
// worker chỉ dọn cache có tên khác CACHE_NAME — mà tên đó không bao giờ đổi.
export const dynamic = "force-static";

const VERSION = process.env.VERCEL_GIT_COMMIT_SHA?.slice(0, 8) ?? String(Date.now());

const SCRIPT = `
const CACHE_NAME = "moveinmate-shell-${VERSION}";
const APP_SHELL = ["/", "/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)),
        ),
      ),
  );
  self.clients.claim();
});

// Chỉ can thiệp GET cùng-origin — API backend (khác origin) và mọi request
// không phải GET (POST/PATCH auth, chat...) đi thẳng ra mạng, không qua cache,
// để không làm hỏng luồng auth/dữ liệu thời gian thực.
self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("/").then((res) => res ?? Response.error())),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ??
        fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        }),
    ),
  );
});

// Phần nhận push chạy hoàn toàn ở service worker nên vẫn hiện khi ứng dụng
// đang đóng. Backend của Hiếu sẽ gửi payload JSON theo contract title/body/url.
self.addEventListener("push", (event) => {
  let payload = { title: "MoveInMate", body: "Bạn có cập nhật mới.", url: "/documents" };
  try { if (event.data) payload = { ...payload, ...event.data.json() }; } catch {}
  event.waitUntil(self.registration.showNotification(payload.title, {
    body: payload.body,
    icon: "/pwa/icon-192",
    badge: "/pwa/icon-192",
    data: { url: payload.url || "/" },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = new URL(event.notification.data?.url || "/", self.location.origin).href;
  event.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
    const existing = windows.find((client) => client.url === target);
    return existing ? existing.focus() : clients.openWindow(target);
  }));
});
`;

export async function GET() {
  return new Response(SCRIPT, {
    headers: {
      "Content-Type": "application/javascript; charset=utf-8",
      // Trình duyệt phải luôn revalidate file sw.js gốc để phát hiện bản mới —
      // cache-control dài hạn ở đây sẽ tái tạo đúng lỗi mà việc này định sửa.
      "Cache-Control": "no-cache",
      "Service-Worker-Allowed": "/",
    },
  });
}
