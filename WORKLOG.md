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

## 2026-08-06

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

## 2026-08-07

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Hiếu | Alembic migration + seed CHECKLIST_ITEMS | | | |
| Hiếu | Tải Thông tư 02/2016/TT-BXD, chuẩn bị KB cho demo GATE 2 | | | |
| Hải | Dựng pipeline ingest: PDF → chunk → embed → Chroma | | | |
| Thu | Trang /onboarding (đang thiếu, là mắt xích bắt buộc của checklist) | | | |

**Tổng kết ngày:**

Ký hiệu trạng thái: ✅ Done · 🔄 WIP · ❌ Blocked
-->
