# MoveInMate

> Cư dân mới phải tự mò hàng loạt thủ tục nhận nhà → AI Agent lập checklist cá nhân hóa và giải đáp thủ tục có trích nguồn, cho cư dân và Ban quản lý chung cư Vinhomes Smart City.

**Trạng thái:** đang phát triển (Phase 1).

| | Đang chạy tại |
|---|---|
| **Ứng dụng** | https://web-ten-ruby-48.vercel.app |
| **API** | https://moveinmate-api-production.up.railway.app |

Xem [`docs/PROJECT_CHARTER.md`](./docs/PROJECT_CHARTER.md) để biết scope và quyết định, [`docs/architecture_diagram.md`](./docs/architecture_diagram.md) để biết kiến trúc, [`docs/DEPLOY.md`](./docs/DEPLOY.md) để deploy.

## Tài khoản dùng thử

Tài khoản do Ban quản lý cấp — cư dân không tự đăng ký. Mật khẩu **dùng chung cho mọi tài khoản demo**: `MoveInMate!2026`

| Email | Vai | Checklist |
|---|---|---|
| `mentor@moveinmate.demo` | **hồ sơ trắng — dành cho người thử lần đầu** | 4 mục nền |
| `bql@moveinmate.demo` | Ban quản lý | — |
| `tran.hong.tuan1@moveinmate.demo` | chủ hộ · có ô tô · 2 gói tiện ích | 10 mục |
| `dang.ngoc.lan5@moveinmate.demo` | người thuê · có xe | 9 mục |
| `duong.ngoc.mai3@moveinmate.demo` | chủ hộ · không xe | 6 mục |
| `pham.thi.dung4@moveinmate.demo` | người thuê · không xe | 6 mục |
| `phan.quang.trang8@moveinmate.demo` | chưa thiết lập hồ sơ | 4 mục |

Hai dòng **6 mục** là cặp đáng xem nhất: cùng số lượng nhưng khác nội dung — chủ hộ được hướng dẫn *cập nhật thông tin cư trú*, người thuê được hướng dẫn *đăng ký tạm trú tại công an phường*. Cá nhân hóa nằm ở nội dung, không ở số lượng.

Muốn tự trải nghiệm từ đầu thì đăng nhập bằng `mentor@moveinmate.demo`, tự điền form onboarding và xem checklist sinh ra theo lựa chọn của mình. **Tài khoản này chỉ trắng một lần** — điền xong là hết. Cần một hồ sơ trắng nữa thì cấp thêm bằng chính chức năng của Ban quản lý (`POST /api/v1/admin/users`), đừng chạy `seed_data`: script đó xoá và dựng lại toàn bộ dữ liệu chứ không khôi phục riêng một tài khoản.

⚠️ `mentor@moveinmate.demo` **phải gõ tay** — màn đăng nhập chỉ liệt kê sáu tài khoản mẫu còn lại, chọn theo hồ sơ tương phản để demo. Các dòng khác trong bảng đều bấm chọn được.

## Vấn đề

Cư dân mới nhận nhà tại chung cư phải hoàn thành nhiều thủ tục rời rạc — đăng ký thẻ cư dân, thẻ xe, internet, ký nội quy, kích hoạt tiện ích — mà không có hướng dẫn tập trung.

- **Cư dân** choáng ngợp, không biết bắt đầu từ đâu, dễ sót việc hoặc làm sai thứ tự.
- **Ban quản lý (BQL)** phải trả lời lặp đi lặp lại cùng những câu hỏi: đăng ký ở đâu, cần giấy tờ gì, hồ sơ đến đâu rồi. Ở các dự án lớn có thể lên tới hàng trăm lượt hỏi mỗi ngày.
- Phát sinh **chi phí vận hành ẩn**: nhân sự CSKH xử lý thủ công, nhập liệu, sai sót hồ sơ, cư dân gọi điện hỏi tiến độ nhiều lần.

**Vì sao app hiện có chưa đủ:** Vinhomes Resident xử lý đặt tiện ích, thanh toán phí, gửi phản ánh — phục vụ cư dân *đã ổn định*. Hồ sơ giấy tờ và thẻ ra/vào vẫn phải làm việc trực tiếp qua BQL. MoveInMate lấp khoảng trống của **4-6 tuần đầu tiên**, khi cư dân chưa biết mình cần làm gì.

## Giải pháp

- **Checklist cá nhân hóa** — cư dân điền form ngắn (chủ hộ hay người thuê, loại căn hộ, có xe, gói tiện ích đã đăng ký); hệ thống sinh đúng danh sách thủ tục cho hoàn cảnh của họ, không phải danh sách chung chung. Dùng rule engine tất định, không dùng LLM.
- **Hỏi đáp thủ tục có trích nguồn** — RAG trên tài liệu của dự án. Nguồn trích dẫn lấy tất định từ bước truy xuất, không do LLM tự liệt kê; không tìm được tài liệu thì hệ thống từ chối trả lời thay vì bịa.
- **Theo dõi tiến độ** — cư dân thấy còn thiếu bước nào; BQL thấy ai đang tắc ở đâu để chủ động hỗ trợ.

Thủ tục thuộc phạm vi BQL được hỗ trợ đầy đủ. Thủ tục thuộc cơ quan bên thứ ba (ví dụ đăng ký tạm trú qua công an) chỉ được hướng dẫn theo quy định công khai và ghi rõ nguồn — hệ thống không mạo nhận đó là quy trình của BQL.

## Người dùng

- **Khách hàng (buyer):** Ban quản lý chung cư — đơn vị triển khai và trả phí.
- **Người dùng cuối:** cư dân mới, được BQL cấp tài khoản. Persona chính là **chủ căn hộ**, có nhánh riêng cho **người thuê**.
- **Phạm vi:** Vinhomes Smart City.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Agent | LangGraph + GPT-4o-mini |
| RAG | ChromaDB + Google `gemini-embedding-001` |
| Backend | FastAPI + Python 3.11 |
| Frontend | Next.js 16 + React 19 + TypeScript (PWA) |
| Database | PostgreSQL qua Supabase |
| Auth | Supabase Auth |
| DevOps | Docker + GitHub Actions · Railway (backend) + Vercel (frontend) |
| Observability | LangSmith — *chưa triển khai, xem [`docs/OPERATIONS.md`](./docs/OPERATIONS.md)* |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/AI20K-Build-Phase-Cohort-3/P-225.git
cd P-225

# 2. Backend
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # điền OPENAI_API_KEY, SUPABASE_*, ...

python -m scripts.check_db         # kiểm tra DATABASE_URL trước khi migrate
alembic upgrade head               # tạo bảng
python -m scripts.seed_data        # 12 checklist item + 40 cư dân giả
python -m scripts.provision_auth   # cấp tài khoản Supabase Auth cho từng hồ sơ

cp web/.env.local.example web/.env.local   # điền NEXT_PUBLIC_SUPABASE_*
uvicorn src.main:app --reload      # http://localhost:8000/docs

# 3. Frontend (terminal khác)
cd web
npm ci
npm run dev                        # http://localhost:3000

# 4. Cài AI logging hook (một lần sau khi clone)
bash scripts/setup_hooks.sh        # Windows: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
```

## Project Structure

```
├── src/                      # Backend Python
│   ├── agents/               # LangGraph — graph, state, nodes
│   ├── api/                  # FastAPI routes
│   ├── models/               # Pydantic schemas + SQLAlchemy models
│   ├── services/             # Rule engine checklist, vectorstore, ingest
│   ├── config.py
│   └── main.py
├── web/                      # Frontend Next.js (PWA)
├── tests/                    # pytest
├── docs/
│   ├── PROJECT_CHARTER.md    # Scope, quyết định, rủi ro — nguồn sự thật
│   ├── architecture_diagram.md
│   └── guide/                # Technical guidebook của chương trình
├── eval/                     # Bằng chứng đánh giá
├── presentation/             # Slide + video demo
├── scripts/                  # AI usage logging hooks
├── Dockerfile
└── .github/workflows/        # CI: ruff + pytest
```

## API Endpoints

| Method | Path | Mô tả | Giai đoạn |
|--------|------|-------|-----------|
| GET | `/health` | Health check | ✅ có |
| GET | `/api/v1/auth/demo-accounts` | Persona mẫu để demo (⚠️ tạm thời) | ✅ có |
| POST | `/api/v1/onboarding` | Lưu hồ sơ cư dân | GATE 2 |
| GET | `/api/v1/checklist` | Checklist cá nhân hóa + % tiến độ | GATE 2 |
| PATCH | `/api/v1/checklist/{id}` | Đánh dấu hoàn thành | GATE 2 |
| POST | `/api/v1/chat` | Hỏi đáp thủ tục (RAG có trích nguồn) | GATE 2 |
| GET | `/api/v1/profile` · PATCH | Xem/sửa hồ sơ | GATE 2 |
| GET | `/api/v1/chat/history` | Lịch sử hội thoại | GATE 2 |
| POST | `/api/v1/admin/users` | BQL tạo tài khoản cư dân | GATE 2 |
| POST | `/api/v1/admin/documents` | BQL nạp tài liệu | W4 |
| CRUD | `/api/v1/admin/faq` | BQL quản lý FAQ | W4 |
| GET | `/api/v1/admin/dashboard` | Tiến độ toàn bộ cư dân | ✅ có |

Chi tiết hợp đồng API: [`docs/architecture_diagram.md`](./docs/architecture_diagram.md) mục 4.3.

## Giới hạn tốc độ (rate limiting)

Bộ đếm tự viết tay trong bộ nhớ tiến trình (`src/services/rate_limit.py`), **không** dùng `slowapi`/`limits` hay Redis — dịch vụ chạy MỘT instance duy nhất (Chroma sống trong tiến trình FastAPI, xem [`docs/DEPLOY.md`](./docs/DEPLOY.md) mục 213), nên một bộ đếm cục bộ là đủ đúng đắn.

Chỉ áp cho các endpoint TỐN TIỀN (gọi LLM, gọi Google embedding, hoặc ghi tệp/nạp tài liệu); mọi endpoint đọc (checklist, dashboard, danh sách hồ sơ/tài liệu — kể cả endpoint frontend poll `embed_status`) **không** bị giới hạn.

| Endpoint | Ngưỡng mặc định | Setting (`src/config.py`) |
|---|---|---|
| `POST /api/v1/chat` | 10 lượt/phút **và** 100 lượt/giờ | `CHAT_RATE_LIMIT_PER_MINUTE`, `CHAT_RATE_LIMIT_PER_HOUR` |
| `POST /api/v1/applications/{id}/attachments` | 20 lượt/phút | `UPLOAD_RATE_LIMIT_PER_MINUTE` |
| `POST /api/v1/admin/documents` | 20 lượt/phút | `UPLOAD_RATE_LIMIT_PER_MINUTE` |

Khoá theo IP client thật (đọc mục đầu `X-Forwarded-For` do Railway forward, không phải IP của proxy — xem docstring `get_client_ip`). Vượt ngưỡng trả **429** kèm header `Retry-After` và thông điệp tiếng Việt yêu cầu chờ, không lộ chi tiết nội bộ.

**Cố tình KHÔNG có trần tổng số request/ngày trên toàn hệ thống.** Đó mới là thứ thật sự bảo vệ hạn mức Google 1000 request/ngày dùng chung cả nhóm, nhưng một trần như vậy tự nó trở thành rủi ro: chạm ngưỡng giữa buổi demo là trợ lý im lặng với **mọi người**, đúng thảm hoạ đang cố tránh. Hạn mức ngày vẫn là rủi ro **được theo dõi thủ công**, không phải rủi ro được chặn bằng code.

## Deliverables Checklist

- [x] Source Code (GitHub)
- [x] README.md
- [x] Architecture Diagram (`docs/architecture_diagram.md`)
- [x] AI Logs (tự động qua pre-push hook)
- [x] Live URL / Deploy — [frontend](https://web-ten-ruby-48.vercel.app) · [backend](https://moveinmate-api-production.up.railway.app/health)
- [ ] Video Demo
- [ ] Pitch Deck (`presentation/`)
- [x] Weekly Journal (`JOURNAL.md`)
- [x] Worklog (`WORKLOG.md`)
- [x] Evaluation Evidence ([`eval/results/report.md`](./eval/results/report.md)) — 35 câu, **32/35 · 91%**

## Team

| Thành viên | Role | Phụ trách |
|------------|------|-----------|
| Nguyễn Trung Hiếu | Backend + Data | FastAPI, schema DB, rule engine checklist, Supabase Auth, thu thập tài liệu KB |
| Nguyễn Việt Hải | AI | Pipeline RAG, LangGraph, prompt, chất lượng truy xuất |
| Nguyễn Minh Thu | Frontend | Next.js PWA, giao diện cư dân và BQL |

**Mentor:** Đặng Hải Lộc · **Chương trình:** VinUni AI20K Build Phase, Cohort 3

## License

MIT
