# Handover — Report API, Settings API, Badge System

**Từ:** Claude (implementation session 30/08)
**Cho:** Agent tiếp theo / Hiếu (BE+Data)
**Ngày:** 2026-08-30
**Spec:** `docs/superpowers/specs/2026-08-29-report-settings-badge-design.md` (rev 2)

---

## 1. Bối cảnh — vì sao có việc này

FE (Thu) báo bốn khoảng trống backend chưa lấp:

1. `GET /admin/applications/report` — chỉ có permission guard, chưa có query logic
2. `GET /admin/staff/report`, `GET /admin/departments/report` — chưa có gì
3. `GET/PATCH /admin/settings` — chưa có gì
4. `user_badges` — bảng có sẵn nhưng không code nào ghi/đọc

Kèm bốn câu cần chốt: SLA "đúng hạn" định nghĩa theo gì · Staff/Department dùng API nào ·
Export sinh file ở BE hay FE · Badge tính lúc nào.

---

## 2. Bài học quan trọng nhất của phiên này

**Spec rev 1 sai bốn điểm nền tảng vì viết mà không đọc code.**

Rev 1 được viết sau khi brainstorm, trước khi mở codebase. Kết quả:

| Rev 1 khẳng định | Sự thật trong code |
|---|---|
| SLA lấy từ `processing_time` | `String(100)` — giá trị `"1–3 ngày làm việc"`, `"Theo lịch nhà mạng"` |
| Dùng `applications.submitted_at` / `approved_at` | Hai cột đó **không tồn tại**; chỉ có `created_at`/`updated_at` |
| Thêm cache Redis/TTL cho report | Không có Redis; deploy chốt **một instance**; quy mô thật 40 cư dân × 13 thủ tục |
| Badge khớp `'thẻ xe' in task_name` | Seed xoá-tạo lại `checklist_items` nên id đổi; tên có biến thể `(chủ hộ)`/`(người thuê)` |

Cả bốn chỉ lộ ra khi verify với codebase. **Đọc code trước khi viết spec** — đây là
cùng một lỗi mà `CLAUDE.md` đã cảnh báo ("Định nghĩa thuật ngữ bằng tài liệu, không bằng
code đang có" — và cũng không bằng phỏng đoán).

Đáng chú ý: đề xuất caching được đưa ra kèm phân tích "ưu/nhược" nghe hợp lý, nhưng đứng
trên tiền đề chưa kiểm (quy mô dữ liệu, hạ tầng). Một khuyến nghị có cấu trúc đẹp vẫn có
thể sai từ gốc.

---

## 3. Quyết định đã chốt

| # | Quyết định | Chọn | Lý do |
|---|---|---|---|
| 1 | Nguồn SLA | Cột mới `sla_business_days INT` | `processing_time` là chuỗi hiển thị, không tính được |
| 2 | Mốc thời gian xử lý | Đọc từ `audit_log` | Đã ghi sẵn, không cần cột mới hay backfill |
| 3 | Export Excel/PDF | FE render từ JSON | Không thêm dependency BE |
| 4 | Badge computation | Event-driven | Badge thẻ cần event đổi trạng thái hồ sơ |
| 5 | Ghi badge | `INSERT ... ON CONFLICT DO NOTHING` | `UNIQUE(user_id, badge_key)` có sẵn |
| 6 | Caching | **Không dùng** | Xem mục 2 |
| 7 | Quyền settings | Thêm `MANAGE_SETTINGS` vào role `admin` | Xem mục 5.1 |

Bốn mặc định đã áp dụng (spec mục 9, **chưa ai phản đối nhưng cũng chưa ai xác nhận**):

- Khoảng SLA lấy **cận trên** — `"1–3 ngày"` → `3`
- `rejected` **có** tính vào `avgProcessingDays` (BQL vẫn tốn công xử lý)
- Staff report theo `assigned_to`, không phải "ai thao tác"
- Badge **không thu hồi** khi untick

---

## 4. Đã làm — 605/605 test pass

### File mới

| File | Nội dung |
|---|---|
| `alembic/versions/20260830100000_add_sla_and_settings.py` | rev `e1b7c3d9a204` |
| `src/services/reporting.py` | `business_days_between()` — hàm thuần |
| `src/services/reports.py` | 3 truy vấn báo cáo |
| `src/services/settings_store.py` | cấu hình hệ thống |
| `src/services/badges.py` | hệ huy hiệu |
| `tests/test_services/test_reporting.py` | 13 test |
| `tests/test_services/test_reports.py` | 27 test |
| `tests/test_services/test_settings.py` | 14 test |
| `tests/test_services/test_badges.py` | 22 test |
| `tests/test_api/test_reports_api.py` | 29 test |

### File sửa

| File | Sửa gì |
|---|---|
| `src/models/db.py` | `+sla_business_days` vào `ChecklistItem`; 3 model mới: `AuditLog`, `UserBadge`, `SystemSetting` |
| `src/models/schemas.py` | `+newly_earned_badges` vào `ChecklistResponse`; `BadgeResponse`, `UserBadgesResponse` |
| `src/models/rbac.py` | `+MANAGE_SETTINGS` vào role `admin` |
| `src/api/routes.py` | 5 endpoint mới; móc badge vào 2 đường ghi |
| `scripts/seed_data.py` | giá trị `sla_business_days`; `validate_sla()`, `validate_badge_categories()` |
| `tests/test_rbac.py` | 2 test chốt cứng chủ ý cũ về `MANAGE_SETTINGS` |

### Endpoint mới

| Method | Path | Permission |
|---|---|---|
| GET | `/api/v1/admin/applications/report` | `VIEW_REPORTS` |
| GET | `/api/v1/admin/departments/report` | `VIEW_REPORTS` |
| GET | `/api/v1/admin/staff/report` | `VIEW_REPORTS` |
| GET | `/api/v1/admin/settings` | `MANAGE_SETTINGS` |
| PATCH | `/api/v1/admin/settings` | `MANAGE_SETTINGS` |
| GET | `/api/v1/user/badges` | `require_resident` |

`PATCH /api/v1/checklist/{item_id}` nay trả thêm `newly_earned_badges: string[]`
(tương thích ngược — FE cũ bỏ qua trường lạ).

---

## 5. Bốn chỗ code làm KHÁC spec

### 5.1 `MANAGE_SETTINGS` thêm vào role `admin`

Quyền này trước chỉ thuộc `super_admin`, nhưng `ROLES` trong `src/models/db.py:48` chỉ có
`("resident", "admin")` — **không tài khoản nào mang được vai `super_admin`**, nên
`/admin/settings` không ai gọi nổi. Đã được người dùng duyệt trong phiên.

`MANAGE_USERS`, `MANAGE_DEPARTMENTS`, `AUDIT_LOG` vẫn nằm ngoài tầm `admin`.

### 5.2 Danh sách quá hạn KHÔNG lọc theo kỳ báo cáo

Spec ngầm hiểu mọi số liệu đều trong kỳ. Sai với `overdue`: "quá hạn" là tình trạng
**hiện tại**, không phải sự kiện trong kỳ. Hồ sơ nộp ba tháng trước mà vẫn treo là thứ BQL
cần thấy nhất — lọc theo kỳ 30 ngày sẽ giấu đúng nó, càng tồn đọng lâu càng chắc bị giấu.

`_load_open_applications()` quét mọi hồ sơ chưa đóng, không giới hạn thời gian.

### 5.3 `date_from=` rỗng hiểu là "không chọn"

FE gửi chuỗi rỗng khi người dùng xoá ô lọc. Trả 422 vào mặt họ vì đúng thao tác đó là vô
lý. Chuỗi **có nội dung** mà sai định dạng vẫn nổ như cũ.

### 5.4 `trends[]` chỉ có dòng cho ngày CÓ dữ liệu

Kỳ 365 ngày sẽ sinh 365 dòng mà phần lớn là số 0. Biểu đồ phía FE tự điền khoảng trống.

### Ngoài kế hoạch: 2 ORM model

`AuditLog` và `UserBadge` — bảng đã có trong migration Phase 2 nhưng **không có model**,
nên `Base.metadata.create_all` trong test không dựng chúng. Hệ quả trước đó: `log_action`
nuốt lỗi "no such table" im lặng, và test report không có gì để đọc.

---

## 6. Bất biến mới — phá là hỏng

- **`sla_business_days` NULL với `third_party_info`.** `seed_data.validate_sla()` chặn.
  Khai SLA cho thủ tục do công an phường xử lý là mạo nhận cam kết của cơ quan khác, và
  report sẽ đếm hồ sơ đó vào tỉ lệ đúng hạn của BQL.
- **Badge khớp theo `checklist_items.category`, không theo tên hay id.**
  `seed_data.validate_badge_categories()` canh hai chuỗi `"Giấy tờ cư dân"` và
  `"Phương tiện"` luôn tồn tại. Gõ sai một chữ thì badge im lặng không bao giờ được trao.
- **Thiếu dữ liệu trả `None`, KHÔNG trả `0`.** `onTimeRate = 0` đọc thành "không hồ sơ
  nào đúng hạn" — báo sai theo hướng có hại. Áp cho mọi hàm trong `reports.py`.
- **Số ngày SLA trích từ KB**, không tự đặt (`data/kb/bql/bql-co-cau-va-quy-trinh.md`
  dòng 86–95). Cùng bất biến charter với số liệu phí.
- **Badge không được làm hỏng request chính.** `safe_check_progress` / `safe_check_card`
  nuốt lỗi và log. Tick checklist thất bại vì lỗi gamification là đánh đổi sai.

---

## 7. VIỆC CÒN LẠI — cần làm tiếp

### 🔴 B1. Migration chưa chạy trên Postgres thật

`alembic upgrade head` **không test được hết trên SQLite**: hai migration Phase 2 có sẵn
(`0fa843848af8`, `20260825120000`) dùng `information_schema`, chỉ Postgres có.

Migration mới đã test riêng (up + down) trên schema dựng từ ORM → sạch cả hai chiều.
Rủi ro thấp (`ADD COLUMN` nullable + `CREATE TABLE` + `CREATE INDEX`) nhưng **chưa chứng
minh được trên DB thật**.

```bash
# PowerShell, không phải Git Bash
alembic upgrade head
```

### 🔴 B2. `sla_business_days` chưa có giá trị trong DB

Cột đã tạo nhưng toàn `NULL` → `onTimeRate` trả `null` cho mọi hồ sơ.

```bash
python -m scripts.seed_data       # nạp SLA vào checklist_items
python -m scripts.provision_auth  # BẮT BUỘC chạy ngay sau
```

**Bỏ bước 2 thì không ai đăng nhập được** — `seed_data` xoá `auth_user_id` (bẫy #4 trong
`CLAUDE.md`).

### ✅ B3. `departmentId` — ĐÃ QUYẾT: bỏ trường (30/08)

**Hiếu chọn hướng "bỏ `departmentId`".** Đã xoá khỏi `reports.py` (trường + truy vấn
`dept_ids` thành thừa) và khỏi spec. Import `Department` giữ lại vì staff report vẫn dùng.
Không test nào khoá trường này nên không phải sửa test; 56 test report vẫn xanh.

Đã kiểm trên DB thật trước khi quyết: `departments` có đúng 4 dòng tiếng Anh, không dòng
nào khớp 4 giá trị `handling_department` tiếng Việt.

Phần dưới đây giữ lại làm hồ sơ vì sao chọn như vậy.

---

#### (Bối cảnh gốc)

`scripts/seed_phase2.py:14-19` seed tên **tiếng Anh**: `Reception`, `Documents`, `Cards`,
`Utilities`. `checklist_items.handling_department` dùng **tiếng Việt**: `Lễ tân & CSKH`,
`An ninh`, `Quản lý tiện ích chung`, `Kỹ thuật (hỗ trợ lắp đặt)`. Không cặp nào khớp.

Thêm hai điều làm phức tạp:

- `seed_phase2.py` là **script chạy tay**, không được gọi từ `seed_data` hay entrypoint
  deploy → bảng `departments` có thể đang **rỗng** trên DB thật.
- Bảng `departments` **không có UNIQUE trên `name`** (comment dòng 120 nói rõ). Sửa
  `DEPARTMENTS` rồi chạy lại sẽ **thêm 4 dòng mới** bên cạnh 4 dòng cũ, không cập nhật.

Report vẫn chạy đúng (nhóm theo tên tiếng Việt), chỉ `departmentId` luôn `null`.

| Hướng | Việc phải làm | Rủi ro |
|---|---|---|
| Sửa `DEPARTMENTS` sang tiếng Việt | Đổi 4 dòng + dọn dòng cũ nếu đã seed | Phải kiểm DB thật; không UNIQUE nên dễ nhân đôi |
| **Bỏ trường `departmentId`** ← đề xuất | Xoá khỏi `reports.py` + spec | FE mất khả năng link sang trang bộ phận |
| Giữ nguyên | Không làm gì | Nợ kỹ thuật im lặng |

**Đề xuất bỏ `departmentId`:** bảng `departments` hiện không có endpoint quản trị nào
(hạng mục cần spec riêng), nên FE chưa có trang bộ phận để link tới. Giữ một trường luôn
`null` để dành chỗ cho tính năng chưa tồn tại là đoán trước nhu cầu.

**Chưa sửa** vì đụng dữ liệu ngoài phạm vi việc này.

### 🟡 B4. Staff report chỉ tính theo `assigned_to`

`performed_by` chỉ được truyền ở `src/api/routes.py:1003`. Hồ sơ đổi trạng thái qua đường
khác có `audit_log.user_id = NULL`.

Đã xử lý bằng cách trả `basis: "assigned_to"` trong response để FE chú thích đúng. Muốn đo
"ai thao tác" thật thì phải truyền `performed_by` ở **mọi** đường ghi trạng thái — việc
riêng, chưa làm.

### 🟢 B5. Ba lỗi ruff

`src/models/rbac.py:6`, `src/services/auth.py:15`, `tests/test_tickets.py:4`.

**Đều có từ trước phiên này** — verify bằng `git stash` trên cây sạch. Không đụng theo
`CLAUDE.md` mục 3 (Surgical Changes). Nêu ra để biết, sửa hay không là quyết định của team.

---

## 8. Ngoài phạm vi — cần spec riêng

| Việc | Lý do hoãn |
|---|---|
| **Staff/Department CRUD** | `MANAGE_DEPARTMENTS` ≠ `MANAGE_SETTINGS`; gộp vào settings sẽ phá ranh giới phân quyền đã tách sẵn |
| **Ngày lễ trong tính SLA** | KB nói SLA trừ cả ngày lễ, nhưng chưa có nguồn dữ liệu — bịa bảng ngày lễ là tự đặt số liệu. Hệ quả: số ngày báo ra có thể **cao hơn** thực tế quanh dịp lễ, tức nghiêng về phía khắt khe với BQL. UI report **phải** nói rõ điều này |
| **Export Excel/PDF** | FE render. `Permission.EXPORT_REPORTS` tồn tại nhưng **không endpoint nào dùng** — chủ ý, không phải sót |
| **Backfill mốc cho hồ sơ trước Phase 2** | Báo qua `coverage` thay vì đoán |
| **FE trang báo cáo/cấu hình** | `web/app/bql/` chưa có `reports/` hay `settings/` — vai Thu |

---

## 9. Ghi chú cho agent tiếp theo

**Môi trường:** dùng `./.venv/Scripts/python.exe`, không phải `python` trần —
`langchain_chroma` không có trong Python hệ thống.

**Lệnh verify:**
```bash
./.venv/Scripts/python.exe -m pytest tests/ -q          # 605 pass
./.venv/Scripts/python.exe -m ruff check src/ tests/    # 3 lỗi có sẵn từ trước
git status --short data/chroma/                         # phải rỗng
```

**Chưa commit gì.** Toàn bộ thay đổi còn trong working tree. `.claude/settings.json`,
`grafana/` và một số file rác (`chunks.txt`, `cloudflared.exe`, `page.html`,
`scripts/fix_alembic*.py`) đã bẩn từ **trước** phiên này — không phải của việc này, đừng
gộp vào commit.

**Thứ tự nên làm:** B1 → B2 → chốt B3 → bàn giao API cho FE.
