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

## 2026-08-15

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nguyễn Minh Thu | Merge `main` (định tuyến US-13 backend của Hiếu) vào `MinhThu` trước khi code phần FE | ✅ Done | `b1eabc4` | |
| Nguyễn Minh Thu | Hiệu ứng fade-in-up so le cho trang đăng nhập (logo/mascot/headline/dải 3 bước, delay 0/150/300/450ms) | ✅ Done | `9b67ffb` | |
| Nguyễn Minh Thu | **US-13 phần 1 — hiện Bộ phận · Nơi nộp · Thời hạn** trên checklist, dùng 3 trường mới `GET /checklist` đã trả sẵn | ✅ Done | `c6e2f25` | |
| Nguyễn Minh Thu | **US-13 phần 2 — nút "Nộp hồ sơ"** trên checklist: type `Application`/`Attachment`, `SubmitApplicationDialog` (bắt riêng 409 đã có hồ sơ mở, 404 mục không thuộc checklist của mình) | ✅ Done | `32cc13e` | |
| Nguyễn Minh Thu | **US-13 phần 3 — tải ảnh minh chứng**: kiểm loại/kích thước phía client trước khi gửi (jpg/png/pdf, tối đa 5MB), bắt riêng 415/413; hồ sơ `self_declared` bắt buộc có ảnh; test end-to-end với backend thật (upload PNG giả, xác nhận 201) | ✅ Done | `9a65d1d` | |
| Nguyễn Minh Thu | **US-13 phần 4 — trang "Hồ sơ đã nộp" dùng dữ liệu thật**: `/requests` đọc `GET /applications` thay mock, tách `applicationStatusLabel`/`applicationStatusTone` dùng chung với `/checklist` để tránh lệch nhãn; xoá `lib/mockRequests.ts` | ✅ Done | `2317870` | |
| Nguyễn Minh Thu | **US-13 phần 5 — trang BQL duyệt & cập nhật hồ sơ**: `/bql/applications` xem hồ sơ mọi cư dân qua `GET /admin/applications`, lọc theo trạng thái/bộ phận; `UpdateApplicationStatusDialog` đổi trạng thái + ghi `bql_note`, báo rõ 409 khi duyệt hồ sơ tự khai chưa có ảnh; kiểm bằng curl với tài khoản admin thật, xác nhận cư dân thường bị chặn 403 | ✅ Done | `5a14c08` | |
| Nguyễn Minh Thu | **US-13 phần 6 — form nộp riêng theo từng thủ tục**, mở nộp cho mục tự khai (`third_party_info` như "Đăng ký tạm trú"): dialog rẽ nhánh đúng theo `item_type` khớp logic backend suy ra `kind` | ✅ Done | `7a4724b` | |
| Nguyễn Minh Thu | **US-13 phần 7 — bắt buộc ảnh giấy tờ** khi nộp thủ tục cần đối chiếu thật (thẻ xe, thẻ cư dân): dialog tách hai bước, khoá nút "Hoàn tất" tới khi tải ít nhất một ảnh | ✅ Done | `0015cd2` | |

**Tổng kết ngày:** Đi trọn luồng US-13 (nộp hồ sơ trực tuyến + upload minh chứng) từ đầu đến cuối trong một ngày, đúng `CONTRACT_US13.md` đã chốt trước với Hiếu — tách rạch ròi hai loại hồ sơ (`bql_actionable` BQL xử lý thật vs. `self_declared` cư dân tự khai, BQL chỉ ghi nhận) để giao diện không mạo nhận quy trình của cơ quan khác. `npx tsc --noEmit` và `npm run build` sạch ở mọi bước, kiểm bằng curl với dữ liệu thật trên backend local xuyên suốt thay vì tin build pass là đủ. Đây cũng là ngày demo GATE 2 (tối nay).

---

## 2026-08-14

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nguyễn Minh Thu | Nâng cấp UI Chat (chip nguồn gọn + modal chi tiết thay accordion, fallback gợi ý khi guard từ chối, panel ngữ cảnh 3 cột: tiến độ radial, checklist rút gọn, hotline BQL), checklist (hiệu ứng pulse khi highlight mục điều hướng tới), Tổng quan (nút "Xem lộ trình →" trỏ tới bước chưa hoàn thành đầu tiên) | ✅ Done | `web/app/chat/`, `web/app/checklist/`, `web/app/dashboard/` | |
| Nguyễn Minh Thu | Sửa bug service worker cache cũ sống mãi qua mọi lần deploy — chuyển `sw.js` từ file tĩnh sang route động, `CACHE_NAME` gắn theo mã commit build | ✅ Done | `bf53798` | |
| Nguyễn Minh Thu | Prototype nội bộ `/prototypes/action-card` (không vào nav) để team xem UI action-card trước khi chốt contract submit thật với BE/AI | ✅ Done | `bf53798` | |
| Nguyễn Minh Thu | V7 — nút 👍/👎 dưới câu trả lời AI Chat | ✅ Done | `a614d2b` | |

**Tổng kết ngày:** Nâng cấp trải nghiệm Chat/checklist/dashboard và vá đúng lỗi sẽ làm mọi bản deploy sau này vô hình với người xem — cache service worker đè code mới. V7 (feedback 👍/👎) mới lưu tạm ở localStorage; chưa đồng bộ backend vì `chat_history` chưa có cột rating và `POST /chat` chưa trả `chat_id` cho tin nhắn vừa gửi — cần Hiếu thêm cột + endpoint để hoàn thiện (`OPERATIONS.md` liệt V7 là việc chung Thu + Hiếu).

---

## 2026-08-12

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Hải | Ingest nốt 3 tài liệu BQL mới + nạp lại 2 file đã viết dày nhưng chưa embed | ✅ Done | `data/chroma/` — KB đủ **412 chunk** | |
| Hiếu | Merge ingest của Hải và frontend của Thu; xác minh cả 4 tài liệu BQL đã vào index | ✅ Done | `dae7c83` | |
| Hiếu | Thay lớp điều hướng phụ thuộc LLM gọi tool (đo **0/5** trên deploy) bằng đối chiếu tất định ở backend — so tên thủ tục với checklist riêng của từng cư dân, khớp đúng một mục mới gắn nút | ✅ Done | `src/api/routes.py`, đo lại **6/6** | |
| Hiếu | Đo lại toàn bộ 35 câu sau khi KB đủ | ✅ Done | **32/35 · 91%** (11/08: 19/35) — `eval/results/report.md` | |
| Hiếu | Sửa nhầm lẫn về nghĩa "agent điều hướng" trong charter: US-13 (nộp hồ sơ trực tuyến, agent định tuyến tới đúng bộ phận BQL) đã có từ 07/08 nhưng bị bỏ sót | ✅ Done | Charter mục 12 | |
| Hiếu | Viết `CLAUDE.md` — sáu cái bẫy đã gây thiệt hại thật và các bất biến thiết kế | ✅ Done | `CLAUDE.md` | |
| Hiếu | **Phân quyền hai chiều**: trước chỉ có `require_admin`, tài khoản BQL vẫn onboarding được và có checklist nhận nhà riêng. Thêm `require_resident`; giữ mở `GET /profile` (frontend đọc `role` từ đây) và `POST /chat` | ✅ Done | `src/api/deps.py`, `src/api/routes.py`, `6304bc5` | |
| Hiếu | Deploy lại Railway và kiểm chứng phân quyền bằng **JWT Supabase thật** trên bản chạy thật, không chỉ unit test | ✅ Done | BQL nhận 403 ở 4 route cư dân, 200 ở `GET /profile` | |
| Hiếu | Vá 2 vết lệch dữ liệu demo (persona "chưa thiết lập" hiện sai số mục; một hồ sơ còn sót mốc onboarding sau đợt test trước) | ✅ Done | Sửa cả generator lẫn dữ liệu đang có | |
| Hiếu | Cập nhật README: 2 URL đang chạy, bảng tài khoản dùng thử, sửa 4 chỗ ghi sai (embeddings là Google chứ không phải OpenAI; LangSmith ghi rõ chưa triển khai) | ✅ Done | `README.md` | |
| Hiếu | Cấp tài khoản trắng cho mentor tự thử luồng onboarding, qua đúng luồng US-00 | ✅ Done | `mentor@moveinmate.demo` | |
| Nguyễn Minh Thu | Deploy lại Vercel kèm nút điều hướng đọc `suggested_action` từ backend | ✅ Done | nút "Đến mục này" trên `/chat` | |
| Nguyễn Minh Thu | US-00 — Dialog BQL tạo tài khoản cư dân (form, gọi `POST /admin/users`, hiện mật khẩu tạm đúng một lần) | ✅ Done | `web/app/components/CreateResidentDialog.tsx`, `web/lib/api.ts` | |
| Nguyễn Minh Thu | Polish UI trạng thái "active" cho onboarding/checklist/sidebar/layout (BQL + cư dân) | ✅ Done | `web/app/onboarding/`, `web/app/checklist/`, `web/app/components/` | |
| Nguyễn Minh Thu | T13 — PWA: manifest, icon (favicon/apple-icon/192/512 sinh bằng `ImageResponse`, không cần asset thiết kế trước), service worker cache app shell (chỉ GET cùng-origin, bỏ qua API backend) | ✅ Done | `web/app/manifest.ts`, `web/app/icon.tsx`, `web/app/pwa/`, `web/public/sw.js` | |
| Nguyễn Minh Thu | Merge nhánh `main` mới nhất (điều hướng AI trong chat, ingest thêm tài liệu BQL của Hiếu/Hải) vào `MinhThu`; xử lý 4 file xung đột tay từng dòng | ✅ Done | merge `ca2a397` | |
| Nguyễn Minh Thu | Tự test toàn bộ luồng sau merge, phát hiện và sửa 4 lỗi thật: hiện nguyên JSON thô khi backend trả lỗi thay vì câu tiếng Việt; service worker cache đè code mới mỗi lần sửa (chỉ bật ở production); admin đăng nhập xong đi vòng qua redirect thừa; lỗi 403 (chưa được gán hồ sơ) rơi vào thông báo chung chung | ✅ Done | `web/lib/api.ts`, `web/app/register-service-worker.tsx`, `web/app/login/page.tsx` | |
| Nguyễn Minh Thu | Redesign trang đăng nhập (mascot AI + dải 3 bước hành trình, ảnh nền) và dashboard BQL (giao diện enterprise sạch, ô tìm kiếm cư dân lọc dữ liệu thật); phần Phase 2 (duyệt HITL, cấu hình AI, biểu đồ phân bố) đánh dấu rõ "Sắp có" và khoá lại, không vẽ số liệu bịa | ✅ Done | `web/app/login/page.tsx`, `web/app/bql/dashboard/page.tsx`, `web/app/components/BQLSidebar.tsx` | |
| Nguyễn Minh Thu | Viết `docs/QA_CHECKLIST.md` — 25 mục test thủ công end-to-end (cư dân + BQL), kèm ghi chú debug các lỗi hay gặp | ✅ Done | `docs/QA_CHECKLIST.md` | |
| Nguyễn Minh Thu | Merge nhánh `MinhThu` vào `main` qua PR | ✅ Done | — | |

**Tổng kết ngày:** Sản phẩm đã chạy thật đầu-cuối trên URL công khai và đo được: eval **32/35 · 91%**, 89 test, coverage 80%. Hai lỗi thiết kế bị phát hiện **bằng phép đo chứ không bằng cảm giác** — nút điều hướng 0/5 và phân quyền một chiều. Về phía frontend: US-00 và T13 (PWA) hoàn tất, merge code mới nhất của Hiếu/Hải và tự chạy thử toàn bộ luồng thay vì tin build pass là đủ — nhờ đó bắt được 4 lỗi thật mà chỉ nhìn code không thấy (lỗi hiển thị JSON thô, service worker cache đè code dev, routing thừa, thông báo lỗi mù mờ). Redesign 2 màn hình chính (đăng nhập, dashboard BQL) theo nguyên tắc minh bạch: phần chưa có API thật thì khoá lại và ghi rõ "Sắp có", không vẽ số liệu/biểu đồ giả cho có vẻ đầy đủ. Còn nợ bên AI: guard hỏng ở vùng biên (3 câu "đúng lĩnh vực nhưng KB không có" vẫn đính trích dẫn dưới câu "tôi không biết"), LangSmith chưa triển khai, chưa có rate limiting. Còn nợ bên frontend: US-09 (CRUD FAQ) và US-08 (upload tài liệu) chưa code — đúng scope W4, backend chưa có endpoint, charter mục 12 yêu cầu chốt contract API bằng văn bản trước khi FE/BE code song song (bài học từ vụ lệch schema 07/08).

⚠️ **Một việc cần theo dõi:** CI GitHub Actions đỏ ở mọi nhánh vì **tài khoản tổ chức vướng thanh toán** (job chết sau 2 giây, chưa từng khởi động), không phải lỗi code — nhóm không có quyền admin để sửa. (Việc code frontend chưa commit/push nêu ở bản ghi trước đã xử lý xong — toàn bộ đã lên `origin/MinhThu` và merge vào `main` trong ngày.)

---

## 2026-08-11

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Nguyễn Minh Thu | Sửa lỗi `API_BASE` rỗng khiến mọi request gọi nhầm vào chính Next.js thay vì backend (`??` không fallback trên chuỗi rỗng) | ✅ Done | `web/lib/api.ts` | |
| Nguyễn Minh Thu | Tích hợp Supabase Auth thật vào trang đăng nhập (form, session, lỗi hiển thị rõ nguyên nhân) | ✅ Done | `web/app/login/page.tsx`, `web/lib/session.ts`, `web/lib/supabase.ts` | |
| Nguyễn Minh Thu | Merge code US-01 (auth JWT thật + route guard) từ nhánh `main` của Hiếu vào `MinhThu`; vá lỗi build phát sinh sau merge (`describeError` bị mất khi gộp `api.ts`) | ✅ Done | merge `0c0a8ed`, `web/lib/api.ts` | |
| Nguyễn Minh Thu | Tạo `Button.tsx` dùng chung (variant primary/secondary/danger, touch-target 44px); chuẩn hoá màu + thang chữ qua Tailwind v4 `@theme`; bỏ font serif Playfair Display gây khó đọc số liệu | ✅ Done | `web/app/components/Button.tsx`, `web/app/globals.css`, `web/app/layout.tsx` | |
| Nguyễn Minh Thu | Nâng cấp UI checklist (nhóm theo category, filter tab), chat (citation nguồn, quick-suggestions, widget nổi), profile (tab), dashboard (số liệu thật) | ✅ Done | `web/app/checklist/`, `web/app/chat/`, `web/app/profile/`, `web/app/dashboard/` | |
| Nguyễn Minh Thu | Tách route `/bql/*` riêng cho Ban quản lý, gate theo `role` | ✅ Done | `web/app/bql/` | |
| Nguyễn Minh Thu | Deploy `web/` lên Vercel (T8): cài CLI, `vercel link`, đặt biến `NEXT_PUBLIC_*` production, `vercel --prod` | ✅ Done | `https://web-ten-ruby-48.vercel.app` | |
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
 