# MoveInMate

> Cư dân mới phải tự mò hàng loạt thủ tục nhận nhà → AI Agent lập checklist cá nhân hóa và giải đáp thủ tục có trích nguồn, cho cư dân và Ban quản lý chung cư Vinhomes Smart City.

> Kiểm tra ngày 30/10/2026: backend, cơ sở dữ liệu và đăng nhập tài khoản demo đều hoạt động. Backend chạy trên Railway gói trả phí và có thể ngừng khi gói hết hạn. Muốn tự chạy, xem [Quick Start](#quick-start) hoặc [`docs/DEPLOY.md`](./docs/DEPLOY.md).

| | Đang chạy tại |
|---|---|
| **Ứng dụng** | https://web-ten-ruby-48.vercel.app |
| **API** | https://moveinmate-api-production.up.railway.app |

Xem [`docs/PROJECT_CHARTER.md`](./docs/PROJECT_CHARTER.md) để biết scope và quyết định, [`docs/architecture_diagram.md`](./docs/architecture_diagram.md) để biết kiến trúc, [`docs/DEPLOY.md`](./docs/DEPLOY.md) để deploy.

## Tài khoản dùng thử

Tài khoản do Ban quản lý cấp — cư dân không tự đăng ký. Mật khẩu **dùng chung cho mọi tài khoản demo**: `MoveInMate!2026`

Trang đăng nhập liệt kê sẵn các persona tương phản — bấm chọn để đăng nhập ngay. Danh sách được sinh động từ dữ liệu, mỗi persona hiển thị số mục checklist cá nhân hóa để thấy sự khác biệt giữa các hồ sơ. Hai cặp đáng xem nhất:

- **Chủ hộ · có ô tô · 2 gói** vs **Người thuê · có xe** — cùng số mục nhưng khác nội dung: chủ hộ được hướng dẫn *cập nhật thông tin cư trú*, người thuê được hướng dẫn *đăng ký tạm trú tại công an phường*.
- **Chủ hộ · không xe** vs **Người thuê · không xe** — số mục giống nhau nhưng người thuê có thêm bước đăng ký tạm trú.

## Vấn đề

Cư dân mới nhận nhà tại chung cư phải hoàn thành nhiều thủ tục rời rạc — đăng ký thẻ cư dân, thẻ xe, internet, ký nội quy, kích hoạt tiện ích — mà không có hướng dẫn tập trung.

- **Cư dân** choáng ngợp, không biết bắt đầu từ đâu, dễ sót việc hoặc làm sai thứ tự.
- **Ban quản lý (BQL)** phải trả lời lặp đi lặp lại cùng những câu hỏi: đăng ký ở đâu, cần giấy tờ gì, hồ sơ đến đâu rồi.
- Phát sinh **chi phí vận hành ẩn**: nhân sự CSKH xử lý thủ công, nhập liệu, sai sót hồ sơ, cư dân gọi điện hỏi tiến độ nhiều lần.

## Giải pháp

- **Checklist cá nhân hóa** — cư dân điền form ngắn (chủ hộ hay người thuê, loại căn hộ, có xe, gói tiện ích); hệ thống sinh đúng danh sách thủ tục cho hoàn cảnh của họ. Dùng rule engine tất định, không dùng LLM.
- **Hỏi đáp thủ tục có trích nguồn** — RAG trên tài liệu của dự án. Nguồn trích dẫn lấy tất định từ bước truy xuất, không do LLM tự liệt kê; không tìm được tài liệu thì hệ thống từ chối trả lời thay vì bịa.
- **Theo dõi tiến độ** — cư dân thấy còn thiếu bước nào; BQL thấy ai đang tắc ở đâu để chủ động hỗ trợ.
- **Nộp hồ sơ trực tuyến** — cư dân bấm nộp từ mục checklist, kèm ảnh minh chứng; BQL duyệt và chuyển trạng thái ngay trên hệ thống.

Thủ tục thuộc phạm vi BQL được hỗ trợ đầy đủ. Thủ tục thuộc cơ quan bên thứ ba (ví dụ đăng ký tạm trú qua công an) chỉ được hướng dẫn theo quy định công khai và ghi rõ nguồn.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Agent | LangGraph + GPT-4o-mini |
| RAG | ChromaDB + Google `gemini-embedding-001` |
| Backend | FastAPI + Python 3.11 |
| Frontend | Next.js 15 + React 19 + TypeScript (PWA) |
| Database | PostgreSQL qua Supabase |
| Auth | Supabase Auth (JWT ES256 + JWKS) |
| DevOps | Docker · Railway (backend) · Vercel (frontend) |
| Observability | log JSON + LangSmith tracing · Prometheus + Grafana · cảnh báo Slack |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/HieuNT316/MoveInMate-AI.git
cd MoveInMate-AI

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
```

## Project Structure

```
├── src/
│   ├── agents/               # LangGraph — graph, state, nodes (đã chuyển sang src/ai/)
│   ├── ai/                   # Form generation, intent detection
│   ├── api/                  # FastAPI routes (25 endpoint)
│   ├── models/               # Pydantic schemas + SQLAlchemy models
│   ├── services/             # Rule engine, vectorstore, storage, auth, PII
│   ├── observability.py      # Structured logging + exception handler
│   ├── config.py
│   └── main.py
├── web/                      # Frontend Next.js (PWA)
├── tests/                    # pytest (197 test, 80% coverage)
├── docs/
│   ├── PROJECT_CHARTER.md    # Scope, quyết định, rủi ro — nguồn sự thật
│   ├── architecture_diagram.md
│   ├── superpowers/          # Plans, specs, handovers
│   └── guide/                # Technical guidebook của chương trình
├── eval/                     # Bằng chứng đánh giá
├── presentation/            # Slide + video demo
├── scripts/                  # Seed, provision, deploy, AI logging hooks
└── .github/workflows/        # CI: ruff + pytest
```

## API Endpoints

`/api/v1` prefix · 25 endpoint · Chi tiết hợp đồng: [`docs/architecture_diagram.md`](./docs/architecture_diagram.md) mục 4.3.

### Authentication & Profile
| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/auth/demo-accounts` | Persona mẫu cho trang đăng nhập |
| GET | `/profile` | Hồ sơ cư dân hiện tại |
| PATCH | `/profile` | Sửa hồ sơ |
| POST | `/onboarding` | Lưu hồ sơ (lần đầu đăng nhập) |

### Checklist
| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/checklist` | Checklist cá nhân hóa + % tiến độ |
| PATCH | `/checklist/{id}` | Đánh dấu hoàn thành |
| GET | `/checklist/{id}/form-schema` | **Mới.** Schema form động cho thủ tục |

### Applications (US-13)
| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/applications` | Nộp hồ sơ cho một mục checklist |
| GET | `/applications` | Hồ sơ của cư dân đang đăng nhập |
| GET | `/applications/{id}/attachments/{aid}/url` | Ký link đọc ảnh tạm thời (hết hạn 5 phút) |

### Chat
| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/chat` | Hỏi đáp thủ tục (RAG có trích nguồn) |
| GET | `/chat/conversations` | Danh sách hội thoại đã lưu |
| GET | `/chat/conversations/{id}/messages` | Toàn bộ lượt hỏi đáp |

### BQL — Residents
| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/admin/users` | Tạo tài khoản cư dân |
| GET | `/admin/dashboard` | Tiến độ toàn bộ cư dân |
| GET | `/admin/residents/{id}` | Toàn cảnh một cư dân (hồ sơ + checklist + hồ sơ đã nộp) |
| PATCH | `/admin/residents/{id}/status` | Khoá/mở tài khoản (`active`/`locked`) |
| POST | `/admin/residents/{id}/reset-password` | Đặt lại mật khẩu tạm |

### BQL — Applications
| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/admin/applications` | Tất cả hồ sơ, lọc theo `status`/`department` |
| PATCH | `/admin/applications/{id}` | Chuyển trạng thái hồ sơ |
| PATCH | `/admin/applications/{id}/attachments/{aid}` | Gán lại loại giấy tờ cho tệp đã tải |
| POST | `/admin/applications/{id}/attachments` | Tải ảnh/PDF minh chứng lên hồ sơ |

### BQL — Knowledge Base
| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/admin/documents` | Dán tiêu đề + nội dung, nạp vào KB ở nền |
| GET | `/admin/documents` | Danh sách tài liệu đã nạp, kèm `embed_status` |

### Health
| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/health` | Health nông — kiểm tiến trình còn sống |
| GET | `/health/deep` | Kiểm DB + Chroma thật; trả **503** nếu một trong hai hỏng |

## Security

- **JWT Supabase ES256 + JWKS** — backend verify chữ ký, đọc `sub` rồi tra sang `users.auth_user_id`. Không nhận `user_id` do client tự khai.
- **`X-User-Id` chỉ dev** — bị chặn cứng khi `APP_ENV=production`.
- **Bucket ảnh private** — ảnh CCCD/VNeID chỉ đọc qua signed URL hết hạn 5 phút. URL được ký khi người dùng thật sự mở ảnh, không ký sẵn hàng loạt.
- **Che PII** — CCCD, email, số điện thoại bị che khỏi `chat_history` trước khi ghi.
- **Rate limiting** — giới hạn theo IP trên endpoint tốn tiền (chat, upload).

## Deliverables Checklist

- [x] Source Code (GitHub)
- [x] README.md
- [x] Architecture Diagram (`docs/architecture_diagram.md`)
- [x] AI Logs (đã nộp cho BTC trong chương trình; phần hook ghi log đã được gỡ khỏi repo này)
- [x] Live URL — [frontend](https://web-ten-ruby-48.vercel.app) · [backend](https://moveinmate-api-production.up.railway.app/health)
- [ ] Video Demo
- [ ] Pitch Deck (`presentation/`)
- [x] Weekly Journal (`JOURNAL.md`)
- [x] Worklog (`WORKLOG.md`)
- [x] Evaluation Evidence (`eval/results/`) — 37 câu hỏi, `scripts/run_eval.py`

### Kết quả đánh giá gần nhất (29/08)

Giám khảo là **Claude Sonnet 5** — một model KHÁC model sinh câu trả lời:

| Chỉ số | Kết quả |
|---|---|
| Khớp từ khoá | 94,6% (35/37) |
| Giám khảo chấm đúng nội dung | **48,6%** |
| Có trích dẫn nguồn hợp lệ | **35,7%** |
| Độ trễ p95 | 5.309 ms (mục tiêu 3.000 ms — **chưa đạt**) |

Bản đo trước đó để model tự chấm bài của chính nó và cho **100%** ở cả ba
tiêu chí. Con số đó không dùng được: khoảng cách giữa 94,6% (khớp từ khoá) và
48,6% (đúng nội dung) cho thấy một câu trả lời có thể chứa đủ từ khoá mà vẫn
sai. Chúng tôi giữ lại con số thấp hơn vì nó phản ánh đúng chất lượng hiện tại
và chỉ ra việc cần làm tiếp.

## Team

| Thành viên | Role | Phụ trách |
|------------|------|-----------|
| Nguyễn Trung Hiếu | Backend + Data | FastAPI, schema DB, rule engine checklist, Supabase Auth, storage, US-13 |
| Nguyễn Việt Hải | AI | RAG pipeline, LangGraph, prompt, form generation |
| Nguyễn Minh Thu | Frontend | Next.js PWA, giao diện cư dân và BQL |

**Mentor:** Đặng Hải Lộc · **Chương trình:** VinUni AI20K Build Phase, Cohort 3

## Vai trò của tôi — Nguyễn Trung Hiếu (Backend + Data)

Dự án nhóm 3 người trong chương trình VinUni AI20K Build Phase. Tôi phụ trách toàn bộ phần backend và dữ liệu:

- **API và cơ sở dữ liệu:** thiết kế API FastAPI (`src/api/`), mô hình SQLAlchemy và 16 migration Alembic, tích hợp PostgreSQL trên Supabase.
- **Rule engine checklist:** `src/services/checklist.py` sinh checklist cá nhân hoá bằng luật tất định theo loại sở hữu, xe, gói tiện ích. Không dùng LLM cho việc này vì thủ tục hành chính cần đúng tuyệt đối và giải thích được. Có test ma trận persona, và `seed_data` kiểm tra khoá `conditions` khi nạp dữ liệu.
- **Xác thực và phân quyền:** xác minh JWT Supabase ES256 qua JWKS, phân vai cư dân và Ban quản lý, chặn header dev `X-User-Id` ở môi trường production.
- **Hồ sơ nhận nhà và định tuyến phòng ban (US-13):** luồng nộp hồ sơ, chuyển đúng bộ phận BQL xử lý và theo dõi trạng thái. Có lưu trữ ảnh giấy tờ ở bucket private, truy cập qua signed URL hết hạn sau 5 phút.
- **Dữ liệu tri thức (KB):** thu thập và soạn tài liệu pháp lý và quy trình trong `data/kb/` bằng `scripts/fetch_legal_kb.py` và `scripts/scrape_kb.py`, làm đầu vào cho pipeline RAG của bạn Hải.
- **Vận hành:** giới hạn tốc độ, `GET /health/deep` kiểm tra DB và Chroma, deploy backend lên Railway bằng Docker, xây dựng bộ chạy đánh giá `scripts/run_eval.py`.

Phần AI (LangGraph, RAG, prompt) do Hải làm, phần giao diện Next.js do Thu làm. Chi tiết phân vai nằm ở [`docs/ROLES_AND_PLAN.md`](./docs/ROLES_AND_PLAN.md).

## License

MIT
