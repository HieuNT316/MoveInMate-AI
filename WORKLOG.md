# Worklog — MoveInMate (Team P-225)

> Ghi lại công việc theo ngày: ai làm gì, kết quả gì.
> Nhật ký theo tuần: [`JOURNAL.md`](./JOURNAL.md) · Scope & quyết định: [`docs/PROJECT_CHARTER.md`](./docs/PROJECT_CHARTER.md)

## Phân công

| Thành viên | Role | Phạm vi |
|------------|------|---------|
| Nguyễn Trung Hiếu | Backend + Data | FastAPI, schema DB, rule engine checklist, Supabase Auth, thu thập và chuẩn bị tài liệu KB |
| Nguyễn Việt Hải | AI | Pipeline RAG, LangGraph, prompt, chunking, chất lượng truy xuất |
| Nguyễn Minh Thu | Frontend | Next.js PWA, giao diện cư dân và BQL |

> ⚠️ **Cột "Time" cần từng người tự điền.** Các dòng dưới ghi lại việc đã làm theo tài liệu và lịch sử git; số giờ thực tế chỉ người làm mới biết.

---

## 2026-08-12

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Thu | US-00 — Dialog BQL tạo tài khoản cư dân (form, gọi `POST /admin/users`, hiện mật khẩu tạm đúng một lần) | ✅ Done | `web/app/components/CreateResidentDialog.tsx`, `web/lib/api.ts` | |
| Thu | Polish UI trạng thái "active" cho onboarding/checklist/sidebar/layout (BQL + cư dân) | ✅ Done | `web/app/onboarding/`, `web/app/checklist/`, `web/app/components/` | |
| Thu | T13 — PWA: manifest, icon (favicon/apple-icon/192/512 sinh bằng `ImageResponse`, không cần asset thiết kế trước), service worker cache app shell (chỉ GET cùng-origin, bỏ qua API backend) | ✅ Done | `web/app/manifest.ts`, `web/app/icon.tsx`, `web/app/pwa/`, `web/public/sw.js` | |

**Tổng kết ngày:** Đẩy sớm US-00 (đã có sẵn contract, không cần chờ) và T13 (PWA, không phụ thuộc backend). Chưa động vào US-09 (CRUD FAQ) và US-08 (upload tài liệu, `POST /admin/documents`) — cả hai đúng scope W4, backend hiện chưa có endpoint, và charter mục 12 yêu cầu chốt contract API bằng văn bản trước khi FE/BE code song song (bài học từ vụ lệch schema 07/08). Cần Hiếu chốt shape request/response trước khi code FE để tránh làm lại.

---

## 2026-08-11

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Thu | Sửa lỗi `API_BASE` rỗng khiến mọi request gọi nhầm vào chính Next.js thay vì backend (`??` không fallback trên chuỗi rỗng) | ✅ Done | `web/lib/api.ts` | |
| Thu | Tích hợp Supabase Auth thật vào trang đăng nhập (form, session, lỗi hiển thị rõ nguyên nhân) | ✅ Done | `web/app/login/page.tsx`, `web/lib/session.ts`, `web/lib/supabase.ts` | |
| Thu | Merge code US-01 (auth JWT thật + route guard) từ nhánh `main` của Hiếu vào `MinhThu`; vá lỗi build phát sinh sau merge (`describeError` bị mất khi gộp `api.ts`) | ✅ Done | merge `0c0a8ed`, `web/lib/api.ts` | |
| Thu | Tạo `Button.tsx` dùng chung (variant primary/secondary/danger, touch-target 44px); chuẩn hoá màu + thang chữ qua Tailwind v4 `@theme`; bỏ font serif Playfair Display gây khó đọc số liệu | ✅ Done | `web/app/components/Button.tsx`, `web/app/globals.css`, `web/app/layout.tsx` | |
| Thu | Nâng cấp UI checklist (nhóm theo category, filter tab), chat (citation nguồn, quick-suggestions, widget nổi), profile (tab), dashboard (số liệu thật) | ✅ Done | `web/app/checklist/`, `web/app/chat/`, `web/app/profile/`, `web/app/dashboard/` | |
| Thu | Tách route `/bql/*` riêng cho Ban quản lý, gate theo `role` | ✅ Done | `web/app/bql/` | |
| Thu | Deploy `web/` lên Vercel (T8): cài CLI, `vercel link`, đặt biến `NEXT_PUBLIC_*` production, `vercel --prod` | ✅ Done | `https://web-ten-ruby-48.vercel.app` | |
| Hiếu | Mở CORS backend Railway cho domain Vercel vừa deploy | ✅ Done | `CORS_ORIGINS` trên Railway | |

**Tổng kết ngày:** T1/T2/T8 hoàn tất, T3 coi như có sẵn nhờ merge code auth thật của Hiếu (`useDemoUser` tự chặn route chưa đăng nhập). Kiểm chứng cuối ngày: `https://web-ten-ruby-48.vercel.app/login` gọi được backend thật, có danh sách 41 tài khoản demo, CORS đã mở. Còn thiếu: T13 (PWA), T10-T11 (upload tài liệu/CRUD FAQ, đúng scope W4 nên chưa gấp).

---

## 2026-08-08

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Hiếu | Lập PROJECT_CHARTER làm nguồn sự thật duy nhất; rà soát và xử lý mâu thuẫn giữa Brief, PRD, user story và schema | ✅ Done | `docs/PROJECT_CHARTER.md` | |
| Hiếu | Chốt persona (chủ hộ chính + nhánh người thuê), phạm vi quy trình (chỉ BQL, bên thứ ba chỉ hướng dẫn công khai), phạm vi địa lý (Smart City) | ✅ Done | Charter mục 1 và 7 | |
| Hiếu | Thiết kế kiến trúc Phase 1: 3 tầng, một graph LangGraph, rule engine tách riêng, lọc checklist trực tiếp | ✅ Done | `docs/architecture_diagram.md` | |
| Hiếu | Cắt Phase 1 thành hai lát `[GATE 2]` / `[W4]` sau khi đối chiếu ~120h effort với 6 ngày còn lại | ✅ Done | Charter mục 4 | |
| Hiếu | Ghim phiên bản thư viện (`==`), cài dependency Phase 1 cho backend | ✅ Done | `requirements.txt` | |
| Hiếu | Cài dependency frontend, bổ sung `@supabase/supabase-js`; xác nhận build sạch | ✅ Done | `web/package.json` | |
| Hiếu | Chuyển tài liệu vào `docs/`, thay template rỗng ở đường dẫn BTC chấm điểm | ✅ Done | `docs/` | |
| Hiếu | Điền README, JOURNAL, WORKLOG | ✅ Done | 3 file ở gốc repo | |

**Tổng kết ngày:** Chuẩn hóa xong toàn bộ tài liệu định hướng và kiến trúc, môi trường sẵn sàng cho cả ba role. Phát hiện quan trọng nhất: các tài liệu nội bộ đang mâu thuẫn nhau về tính cá nhân hóa — thứ mà đề bài ghi rõ là yêu cầu bắt buộc. Đã xử lý trước khi ai viết dòng code nào.

---

## 2026-08-05

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Cả nhóm | Báo cáo GATE 1: roadmap, use case, user story | ✅ Done | Slide GATE 1 | |

**Tổng kết ngày:** Qua GATE 1.

---

## 2026-08-03 → 2026-08-04

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Cả nhóm | Liên hệ BQL Vinhomes xin tài liệu quy trình onboarding | ❌ Blocked | Bị từ chối, lý do "thủ tục đã công khai" | |
| Cả nhóm | Tìm tài liệu công khai thay thế | 🔄 WIP | Tài liệu chỉ mở cho cư dân; chuyển sang chiến lược nhiều nguồn | |

**Tổng kết:** Nguồn dữ liệu chính bị chặn. Đặt cổng quyết định 13/08 và chuẩn bị phương án dự phòng bằng Thông tư 02/2016/TT-BXD.

---

## 2026-08-02

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Cả nhóm | Soạn PRD v0.1 | ✅ Done | PRD (bối cảnh, khách hàng, scope P0/P1/P2, luồng người dùng, NFR) | |

---

## 2026-08-01

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Cả nhóm | Họp mentor lần 2 | ✅ Done | Mentor đề xuất khảo sát BQL Vinhomes | |

**Tổng kết ngày:** Mốc nhóm bắt đầu làm việc nghiêm túc.

---

<!-- Việc sắp tới — điền khi làm xong

## 2026-08-08

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Hiếu | Alembic migration + seed CHECKLIST_ITEMS | | | |
| Hiếu | Tải Thông tư 02/2016/TT-BXD, chuẩn bị KB cho demo GATE 2 | | | |
| Hải | Dựng pipeline ingest: PDF → chunk → embed → Chroma | | | |
| Thu | Trang /onboarding (đang thiếu, là mắt xích bắt buộc của checklist) | | | |

**Tổng kết ngày:**

Ký hiệu trạng thái: ✅ Done · 🔄 WIP · ❌ Blocked
-->
