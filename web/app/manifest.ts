import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "MoveInMate AI",
    short_name: "MoveInMate",
    description:
      "Trợ lý AI hỗ trợ cư dân nhận nhà: checklist cá nhân hóa, hỏi đáp thủ tục có trích nguồn.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#f0f8ff",
    theme_color: "#002d62",
    lang: "vi",
    icons: [
      { src: "/pwa/icon-192", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/pwa/icon-192", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/pwa/icon-512", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/pwa/icon-512", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
