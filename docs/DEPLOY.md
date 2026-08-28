# Hướng dẫn deploy

**Cập nhật:** 19/08/2026 (rà soát đồng bộ tài liệu ↔ mã nguồn, Task 22)

| Thành phần | Trạng thái | URL |
|---|---|---|
| Backend (Railway) | ✅ đang chạy | https://moveinmate-api-production.up.railway.app |
| Frontend (Vercel) | ✅ đang chạy | https://web-ten-ruby-48.vercel.app |
| Database (Supabase) | ✅ đang chạy | project `sjnpokwczrmyppwhtisu` |

---

## 0. Đọc trước — ràng buộc ảnh hưởng tới CẢ HAI bên

**Repo là private và thuộc org `AI20K-Build-Phase-Cohort-3`. Không ai trong nhóm có quyền admin:**

```
HieuNT316       admin=false  push=true
HaiVietahihi    admin=false  push=true
MinhThu200401   admin=false  push=true
```

Hệ quả: **Railway và Vercel đều KHÔNG nhìn thấy repo** khi kết nối qua GitHub. Bạn sẽ gặp màn hình *"We still can't find this repository"*. Đó không phải sai URL, cũng không phải bạn làm sai bước nào — cài GitHub App vào một org là quyền của **owner org (BTC)**.

Đừng mất thời gian thử lại. **Cả hai bên đều deploy bằng CLI từ máy cá nhân**, không cần quyền GitHub nào.

**Đánh đổi:** không tự deploy khi push. Mỗi lần cập nhật phải chạy lại lệnh deploy bằng tay.

> Vẫn nên nhắn BTC xin duyệt GitHub App cho org để sau GATE 2 chuyển sang auto-deploy — nhưng đừng ngồi chờ.

---

## A. Backend — Railway (đã xong, đây là cách cập nhật)

### A.1 Bẫy phải biết trước

**Chạy mọi lệnh `railway` từ PowerShell, KHÔNG dùng Git Bash.** CLI lưu liên kết project theo đường dẫn Windows `D:\Projects\...`; Git Bash đứng ở `/d/Projects/...` nên `railway status` sẽ báo *"No linked project found"* dù liên kết vẫn còn nguyên.

**`railway up` đóng gói THƯ MỤC HIỆN TẠI, không phải commit.** Chạy `git status` trước mỗi lần deploy, nếu không rất dễ đẩy code nháp lên production.

### A.2 Cập nhật code đã deploy

```powershell
git status                    # phải sạch
railway up
```

Build mất khoảng 8 phút (image ~1 GB vì cây phụ thuộc ML).

### A.3 Đổi biến môi trường

Đừng gõ tay — `SUPABASE_SERVICE_KEY` dài 219 ký tự, và gõ vào dòng lệnh là đẩy secret vào lịch sử PowerShell.

```powershell
python -m scripts.railway_env --dry-run    # xem trước, giá trị đã che
python -m scripts.railway_env              # đẩy thật
```

Script đọc từ `.env`, truyền giá trị qua stdin nên không secret nào lên dòng lệnh. Nó cũng chặn ba lỗi `DATABASE_URL` phổ biến và **cố ý không đẩy `PORT`** (Railway tự cấp; đặt tay là health check trượt).

### A.4 Biến trên Railway

| Biến | Ghi chú |
|---|---|
| `APP_ENV=production` | **Bắt buộc.** Bật chốt chặn header `X-User-Id` |
| `DATABASE_URL` | Chuỗi **Session pooler** của Supabase, cổng 5432 |
| `SUPABASE_URL` · `SUPABASE_ANON_KEY` · `SUPABASE_SERVICE_KEY` · `SUPABASE_JWT_SECRET` | |
| `CHAT_PROVIDER=openai` · `OPENAI_API_KEY` | |
| `GOOGLE_API_KEY` | embeddings |
| `CORS_ORIGINS` | **Phải cập nhật sau khi có domain Vercel** — xem mục C |
| ~~`PORT`~~ | **Đừng đặt** |

### A.5 Kiểm chứng sau deploy

```bash
curl https://moveinmate-api-production.up.railway.app/health
# {"status":"ok","env":"production"}

curl -o /dev/null -w "%{http_code}\n" \
  -H "X-User-Id: 1" \
  https://moveinmate-api-production.up.railway.app/api/v1/profile
# 401
```

**Câu thứ hai quan trọng hơn câu đầu.** Ra `200` nghĩa là `APP_ENV` chưa vào, và đang để một URL công khai mà ai đặt header cũng thành Ban quản lý.

---

## B. Frontend — Vercel (phần của Thu)

### B.1 Cài CLI và đăng nhập

```bash
npm i -g vercel
cd web          # QUAN TRỌNG: đứng trong web/, không phải gốc repo
vercel login
```

Đứng trong `web/` để Vercel coi đó là thư mục gốc của dự án. Chạy từ gốc repo thì nó sẽ thấy cả backend Python và cấu hình sai.

### B.2 Tạo project

```bash
vercel link
```

Chọn **Create a new project**, đặt tên `moveinmate`. Framework Next.js được nhận tự động.

### B.3 Đặt biến môi trường — **làm TRƯỚC khi deploy**

Biến `NEXT_PUBLIC_*` được **nhúng thẳng vào bundle lúc build**, không đọc lúc chạy. Đặt sau khi build thì phải build lại mới có tác dụng.

```bash
vercel env add NEXT_PUBLIC_API_URL production
# dán: https://moveinmate-api-production.up.railway.app/api/v1

vercel env add NEXT_PUBLIC_SUPABASE_URL production
# dán: https://sjnpokwczrmyppwhtisu.supabase.co

vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
# dán: anon key (xin Hiếu, hoặc lấy ở Supabase → Settings → API)
```

Ba giá trị này giống hệt file `web/.env.local` trên máy Hiếu.

> **Chỉ dùng ANON key.** `SUPABASE_SERVICE_KEY` bỏ qua toàn bộ phân quyền và chỉ được nằm ở backend. Mọi biến `NEXT_PUBLIC_*` đều lộ ra trình duyệt.

### B.4 Deploy

```bash
vercel --prod
```

Ghi lại domain nó in ra, dạng `https://moveinmate-xxx.vercel.app`.

### B.5 Kiểm chứng

Mở `https://<domain-vercel>/login`. Phải thấy trang đăng nhập kèm danh sách tài khoản demo.

**Nếu danh sách trống hoặc báo "Không kết nối được backend"** → `NEXT_PUBLIC_API_URL` sai, hoặc CORS chưa mở (mục C).

---

## C. Bắt tay giữa hai bên — CORS

Backend chỉ nhận request từ domain có trong `CORS_ORIGINS`. Hiện đang là `http://localhost:3000`, nên **trang Vercel sẽ không gọi được API** cho tới khi mở.

Sau khi Thu có domain, **Hiếu chạy** (từ PowerShell, thư mục gốc repo):

```powershell
python -m scripts.railway_env --cors "https://<domain-vercel>.vercel.app"
railway up
```

Nhiều domain thì ngăn bằng dấu phẩy, **không có khoảng trắng**:

```powershell
python -m scripts.railway_env --cors "https://moveinmate.vercel.app,http://localhost:3000"
```

Giữ `localhost:3000` để vẫn dev được ở máy.

### Kiểm chứng CORS

```bash
curl -s -D - -o /dev/null \
  -H "Origin: https://<domain-vercel>.vercel.app" \
  https://moveinmate-api-production.up.railway.app/api/v1/auth/demo-accounts \
  | grep -i access-control-allow-origin
```

Không có dòng nào trả về nghĩa là chưa mở.

---

## D. Tài khoản demo

41 tài khoản Supabase đã được cấp bằng `scripts/provision_auth.py`.

**Mật khẩu dùng chung:** `MoveInMate!2026`

Bấm thẳng vào tài khoản mẫu ở trang đăng nhập là tự điền email và mật khẩu.

| Persona | Email |
|---|---|
| Ban quản lý | `bql@moveinmate.demo` |
| Chủ hộ · 2PN · có ô tô · pool, gym | `tran.hong.tuan1@moveinmate.demo` |
| Chủ hộ · studio · không xe | `duong.ngoc.mai3@moveinmate.demo` |
| Người thuê · 2PN · có ô tô · gym | `dang.ngoc.lan5@moveinmate.demo` |
| Người thuê · 1PN · không xe | `pham.thi.dung4@moveinmate.demo` |

---

## E. Những chỗ đã vấp — đọc để khỏi vấp lại

| Triệu chứng | Nguyên nhân thật |
|---|---|
| Railway/Vercel *"can't find this repository"* | Repo private thuộc org, không ai có admin. Dùng CLI |
| `railway status` báo *"No linked project found"* | Đang chạy từ Git Bash. Chuyển sang PowerShell |
| Health check chờ mãi không lên nhưng app vẫn chạy | `Invoke-WebRequest` cần chế độ tương tác. Dùng `curl` |
| `railway init` xong mà `railway up` không có service | `init` chỉ tạo project rỗng. Chạy `railway add --service <tên>` |
| Trang Vercel gọi API bị chặn | `CORS_ORIGINS` chưa có domain Vercel — mục C |
| Đổi `NEXT_PUBLIC_*` mà không thấy tác dụng | Biến nhúng lúc build. Phải `vercel --prod` lại |
| DB báo `connection refused` / treo rồi timeout | Dùng nhầm chuỗi Direct (chỉ IPv6). Đổi sang Session pooler |
| Migration lỗi trên Railway | Dùng nhầm cổng 6543 (Transaction pooler). Dùng 5432 |

---

## F. Việc còn nợ sau GATE 2

- ~~**Chroma đang nướng thẳng vào image.**~~ **Đã xử lý 18/08** — gắn Railway Volume vào `/app/data/chroma`. Volume mới gắn thì rỗng, nên `src/services/chroma_seed.py` tự chép bản mồi (đóng gói sẵn trong image ở `/app/data/chroma_seed`) sang volume lúc khởi động nếu volume còn trống, không đè nếu BQL đã nạp tài liệu qua production. Chi tiết: `docs/architecture_diagram.md` mục 2.
- **Không auto-deploy.** Xin BTC duyệt GitHub App cho org.
- **Chỉ chạy được một instance.** Chroma nằm trong cùng tiến trình FastAPI; scale ngang sẽ khiến mỗi instance có một vector store riêng. Không bật auto-scale.

## G. Log tự động che mật khẩu — giới hạn cần biết khi đổi mật khẩu DB

`safe_database_url()` (`src/config.py`) và bộ lọc log JSON (`src/observability.py`) đều dùng chung một regex để che phần mật khẩu trong `DATABASE_URL` trước khi in ra: `(://[^:\s]+:)[^@\s]+(@)`. Class ký tự `[^@\s]+` dừng lại ở ký tự `@` ĐẦU TIÊN nó gặp — nếu mật khẩu tự nó chứa `@`, regex chỉ che được phần mật khẩu TRƯỚC ký tự `@` đó, phần còn lại lọt ra log nguyên văn.

Mật khẩu Supabase hiện tại không chứa `@` nên chưa lộ gì. Nhưng ai đổi mật khẩu DB (xoay vòng credential) cần tránh chọn mật khẩu có `@`, hoặc phải vá regex trước — redaction hỏng ÂM THẦM, không có cảnh báo nào khi điều đó xảy ra.

---

## H. Prometheus & Grafana

### Metrics Endpoint

Backend expose metrics ở `GET /api/v1/metrics` ở định dạng Prometheus text:

| Metric | Type | Mo ta |
|---|---|---|
| `moveinmate_requests_total` | counter | Tong so request (5 phut cua so) |
| `moveinmate_error_rate` | gauge | Ty le loi 5xx (0.0-1.0) |
| `moveinmate_latency_p95_ms` | gauge | p95 do tre (ms) |
| `moveinmate_cost_today_usd` | gauge | Tong chi phi hom nay ($) |
| `moveinmate_no_context_ratio` | gauge | Ty le tra loi khong co nguon (0.0-1.0) |

### Thresholds Alert

| Nguong | Dieu kien kich hoat |
|---|---|
| Error rate > 1% | Alert Slack trong 5 phut |
| p95 latency > 8s | Alert Slack |
| Cost/day > $10 | Alert Slack |
| Health check fail 3 lan lien tiep | Alert Slack |

Cooldown 5 phut giua cac alert de khong spam.

### Thiet lap

**1. Prometheus scrape backend:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'moveinmate'
    scrape_interval: 30s
    static_configs:
      - targets: ['moveinmate-api-production.up.railway.app']
    metrics_path: '/api/v1/metrics'
```

**2. Import Grafana dashboard:**

Dashboard JSON nam tai `grafana/dashboards/moveinmate-overview.json`. Import vao Grafana qua UI (Dashboards → Import) hoac API.

**3. Thiet lap Slack webhook (optional):**

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
ALERT_COST_DAILY_THRESHOLD=10.0
```

Neu khong co webhook, alert van kiem tra nhung chi log warning, khong gui Slack.

**4. Variables can thiet:**

| Variable | Gia tri |
|---|---|
| `DS_PROMETHEUS` | Data source Prometheus da cau hinh |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |
| `ALERT_COST_DAILY_THRESHOLD` | Ngưỡng chi phí alert (mặc định $10/ngày) |
