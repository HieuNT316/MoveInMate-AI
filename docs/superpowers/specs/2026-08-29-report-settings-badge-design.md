# Report, Settings & Badge System — Design Specification

**Ngày:** 2026-08-29 (rev 2 — 2026-08-30, viết lại sau khi đối chiếu codebase)
**Trạng thái:** Draft — chờ team review
**Phạm vi:** Report APIs, Settings API, Badge System
**Vai trò:** Hiếu (BE+Data)

---

## 0. Ghi chú phiên bản

Rev 1 dựa trên giả định chưa kiểm chứng và **sai ở bốn điểm nền tảng**. Rev 2 viết
lại sau khi đọc code. Bảng dưới ghi lại để không ai đi lại vết cũ:

| Rev 1 viết | Thực tế trong code | Hệ quả |
|---|---|---|
| SLA lấy từ `processing_time` | `String(100)`, giá trị `"1–3 ngày làm việc"`, `"Theo lịch nhà mạng"` ([db.py:172](../../../src/models/db.py)) | `onTimeRate` không tính được → cần cột mới |
| `applications.submitted_at` / `approved_at` | Chỉ có `created_at` / `updated_at` ([db.py:259-264](../../../src/models/db.py)) | Mốc thời gian chuyển trạng thái phải lấy từ `audit_log` |
| Thêm cache Redis/TTL cho report | Không có Redis; [DEPLOY.md:213](../../DEPLOY.md) chốt **một instance**; quy mô thật 40 cư dân × 13 thủ tục | Bỏ caching — xem mục 1.3 |
| Badge nhận diện thẻ bằng `'thẻ xe' in task_name` | Seed **xoá và tạo lại** `checklist_items` ([seed_data.py:392](../../../scripts/seed_data.py)) nên id không ổn định; tên có biến thể `(chủ hộ)`/`(người thuê)` | Map bằng `category`, xem mục 4.4 |

---

## 1. Quyết định thiết kế

### 1.1 Bảng quyết định

| # | Quyết định | Chọn | Lý do |
|---|---|---|---|
| 1 | Nguồn SLA | Thêm cột `sla_business_days INT` vào `checklist_items` | `processing_time` là chuỗi hiển thị, không tính được. Số ngày trích từ bảng định tuyến trong KB, không tự đặt. |
| 2 | Mốc thời gian xử lý | Đọc từ `audit_log` (`action = 'application.status_changed'`) | Đã ghi sẵn ([store.py:573,602](../../../src/services/store.py)), không cần cột mới hay backfill. |
| 3 | Export Excel/PDF | FE render từ JSON | Không thêm dependency BE (`openpyxl`/`reportlab`). |
| 4 | Badge computation | Event-driven | `resident_card`/`vehicle_card` cần event đổi trạng thái hồ sơ. |
| 5 | Ghi badge | `INSERT ... ON CONFLICT DO NOTHING` | `UNIQUE(user_id, badge_key)` đã có sẵn trong migration. Tránh race condition của check-then-insert. |
| 6 | Caching | **Không dùng** | Xem 1.3. |

### 1.2 Vì sao thêm cột thay vì parse chuỗi

Giá trị `processing_time` hiện có trong seed: `"Trong ngày"`, `"1–3 ngày làm việc"`,
`"1–2 ngày làm việc"`, `"2–5 ngày làm việc"`, `"Theo lịch nhà mạng"`, `"Đặt trước 24 giờ"`.

Parse được ba dạng đầu, hai dạng cuối thì không — chúng không phải thời hạn xử lý
của BQL. Một hàm parse sẽ im lặng đoán sai khi ai đó thêm giá trị mới, đúng kiểu lỗi
mà bất biến "key của `conditions` phải nằm trong `PROFILE_FIELDS`" đang chống.

Cột riêng cho phép `NULL` mang nghĩa rõ: **thủ tục này không có SLA của BQL**, và
`seed_data` validate được lúc nạp.

### 1.3 Vì sao KHÔNG cache

- Không có Redis trong `requirements.txt`, thêm vào là thêm dependency + infra.
- [DEPLOY.md:213](../../DEPLOY.md): *"Chỉ chạy được một instance... Không bật auto-scale."*
- Quy mô thật: `--residents` mặc định **40** ([seed_data.py:377](../../../scripts/seed_data.py)),
  13 mục checklist. Report aggregate trên vài trăm dòng.
- [rate_limit.py](../../../src/services/rate_limit.py) đã lập tiền lệ: tự viết bộ đếm
  in-memory, *"không cần Redis hay kho chia sẻ"*.

Cache invalidation ở đây phức tạp hơn chính query nó tăng tốc. Nếu sau này report chậm
thật, xử lý bằng **index** trên `audit_log(resource_type, action, created_at)` trước.

---

## 2. Thay đổi database

### 2.1 Cột `sla_business_days`

```python
# alembic/versions/<rev>_add_sla_and_settings.py

def upgrade() -> None:
    op.add_column(
        "checklist_items",
        sa.Column("sla_business_days", sa.Integer(), nullable=True),
    )
    op.create_table(
        "system_settings",
        sa.Column("setting_key", sa.String(length=100), nullable=False),
        sa.Column("setting_value", JSONType, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("setting_key"),
    )
    # Index phục vụ mọi report query dựa trên audit_log
    op.create_index(
        "idx_audit_action_created",
        "audit_log",
        ["action", "created_at"],
    )
```

`JSONType = JSON().with_variant(JSONB, "postgresql")` ([db.py:46](../../../src/models/db.py)) —
dùng cho cả SQLite (test) lẫn Postgres, đúng nếp của repo. Không dùng `JSONB` trần.

`setting_key` làm primary key luôn, bỏ cột `setting_id` thừa của rev 1.

### 2.2 Giá trị SLA — trích nguồn

Từ bảng định tuyến `data/kb/bql/bql-co-cau-va-quy-trinh.md` dòng 86–95. **Không tự đặt số**
(bất biến charter: số liệu phải trích nguồn).

| Thủ tục | `processing_time` (KB) | `sla_business_days` |
|---|---|---|
| Ký nội quy toà nhà | Trong ngày | 1 |
| Làm thẻ cư dân (chủ hộ) | 1–3 ngày làm việc | 3 |
| Làm thẻ cư dân (người thuê) | 1–3 ngày làm việc | 3 |
| Đăng ký thẻ xe | 1–2 ngày làm việc | 2 |
| Đăng ký chỗ đỗ xe cố định | 2–5 ngày làm việc | 5 |
| Đăng ký thẻ thang máy | Trong ngày | 1 |
| Kích hoạt thẻ bể bơi | Trong ngày | 1 |
| Kích hoạt thẻ phòng gym | Trong ngày | 1 |
| Đăng ký chuyển đồ vào căn hộ | Đặt trước 24 giờ | `NULL` |
| Đăng ký internet và truyền hình | Theo lịch nhà mạng | `NULL` |
| Đăng ký tạm trú (công an phường) | — (`third_party_info`) | `NULL` |
| Cập nhật thông tin cư trú | — (`third_party_info`) | `NULL` |

**Quy ước:** lấy **cận trên** của khoảng — "đúng hạn" nghĩa là không vượt cam kết tối đa.
`NULL` = không có SLA của BQL (thủ tục ngoài phạm vi, hoặc phụ thuộc bên thứ ba).

**Bất biến mới, `seed_data` validate:** `item_type == "third_party_info"` ⟹
`sla_business_days IS NULL`. Cùng lý do với bất biến `handling_department` hiện có.

### 2.3 Ngày làm việc

KB dòng 127: *"Thời hạn tính theo ngày làm việc, không tính thứ Bảy, Chủ nhật và ngày lễ."*

**Phạm vi v1:** đếm ngày làm việc **loại trừ T7/CN**, KHÔNG xử lý ngày lễ — dự án chưa
có bảng ngày lễ, và bịa một bảng ngày lễ là tự đặt dữ liệu. Hàm `business_days_between()`
đặt trong `src/services/reporting.py`, thuần tuý, test được không cần DB.

Giới hạn này **phải hiển thị ở UI report**: "Đúng hạn tính theo ngày làm việc, chưa trừ ngày lễ."

---

## 3. Report APIs

### 3.1 Nguồn dữ liệu mốc thời gian

`applications` không có `submitted_at`/`approved_at`. Dùng:

- **Mốc nộp** = `applications.created_at` (hàng chỉ sinh khi cư dân nộp).
- **Mốc chuyển trạng thái** = `audit_log.created_at` với
  `action = 'application.status_changed'`, `resource_type = 'application'`,
  `new_value->>'status' = :status`.

```sql
-- Mốc lần ĐẦU vào trạng thái đích. Một hồ sơ có thể quay lại 'processing'
-- sau 'needs_info'; lần đầu mới là lúc BQL thực sự chốt.
SELECT resource_id, MIN(created_at) AS reached_at
FROM audit_log
WHERE action = 'application.status_changed'
  AND resource_type = 'application'
  AND new_value ->> 'status' = :status
GROUP BY resource_id
```

**Cảnh báo dữ liệu:** `performed_by` chỉ được truyền ở một chỗ
([routes.py:1003](../../../src/api/routes.py)); hồ sơ đổi trạng thái qua đường khác sẽ có
`audit_log.user_id = NULL`. Staff report vì vậy chỉ tính được trên
`applications.assigned_to`, không phải "ai bấm nút" — xem 3.4.

**Cảnh báo dữ liệu 2:** `audit_log` chỉ có từ khi Phase 2 deploy. Hồ sơ cũ hơn không có
mốc chuyển trạng thái → bị loại khỏi `avgProcessingDays`. Response trả `coverage` để FE
nói rõ, không im lặng báo số thiếu.

### 3.2 `GET /api/v1/admin/applications/report`

Permission: `VIEW_REPORTS`

Query: `date_from`, `date_to` (ISO date, mặc định 30 ngày gần nhất), `overdue_limit` (mặc định 50).

```typescript
interface ApplicationsReport {
  period: { dateFrom: string; dateTo: string };

  summary: {
    total: number;
    byStatus: Record<string, number>;   // key theo APPLICATION_STATUSES
    avgProcessingDays: number | null;   // null khi chưa có hồ sơ nào đóng
    onTimeRate: number | null;          // null khi mẫu = 0
  };

  coverage: {                            // minh bạch chất lượng số liệu
    closedInPeriod: number;
    measurable: number;                  // có đủ mốc audit_log VÀ có sla_business_days
    excludedNoAudit: number;
    excludedNoSla: number;
  };

  trends: { date: string; created: number; closed: number }[];

  overdue: {
    applicationId: number;
    residentName: string;
    apartment: string;
    procedureName: string;
    createdAt: string;
    businessDaysElapsed: number;
    slaBusinessDays: number;
    assignedTo: string | null;
  }[];
  overdueTotal: number;                  // tổng thật, `overdue` đã cắt theo limit
}
```

**Định nghĩa tính toán — chốt rõ:**

- `avgProcessingDays`: trung bình `business_days_between(created_at, reached_at)` với
  `reached_at` = lần đầu đạt `approved` hoặc `delivered`. Chỉ tính hồ sơ **đóng trong kỳ**.
- `onTimeRate` = `on_time / measurable`, trong đó:
  - mẫu số `measurable` = hồ sơ đóng trong kỳ, **có** mốc audit **và** `sla_business_days IS NOT NULL`
  - `on_time` = số hồ sơ có `business_days_between(...) <= sla_business_days`
  - `measurable == 0` → trả `null`, **không trả 0** (0 đọc thành "đúng hạn 0%", sai nghĩa)
- `rejected` **được tính** vào `avgProcessingDays` — BQL vẫn tốn công xử lý.
- `overdue`: hồ sơ **chưa đóng**, `sla_business_days IS NOT NULL`, và
  `business_days_between(created_at, now) > sla_business_days`.

### 3.3 `GET /api/v1/admin/departments/report`

Permission: `VIEW_REPORTS`. Query: `date_from`, `date_to`, `department_id?`.

Bộ phận suy ra từ `checklist_items.handling_department` (**chuỗi tên**), không phải
`departments.department_id` — `applications` không có FK tới `departments`
(cố ý: [db.py:208](../../../src/models/db.py) "tra thẳng từ `checklist_items` mỗi lần đọc").

```typescript
interface DepartmentsReport {
  period: { dateFrom: string; dateTo: string };
  departments: {
    handlingDepartment: string;          // tên từ checklist_items
    total: number;
    open: number;
    unassigned: number;
    overdue: number;
    avgProcessingDays: number | null;
    measurable: number;
    bottlenecks: {                        // thủ tục chậm nhất trong bộ phận
      procedureName: string;
      avgProcessingDays: number | null;
      openCount: number;
    }[];
  }[];
}
```

**Không có `departmentId`** (bỏ ngày 30/08). Bảng `departments` chứa tên tiếng Anh
(`Reception`, `Documents`, `Cards`, `Utilities` — `scripts/seed_phase2.py`), còn
`handling_department` dùng tiếng Việt (`Lễ tân & CSKH`, `An ninh`, …) — đã kiểm trên DB
thật, không cặp nào khớp nên trường đó luôn `null`.

Giữ một trường luôn rỗng để dành cho trang quản lý bộ phận **chưa tồn tại** là đoán trước
nhu cầu. Khi nào có trang đó thì nối lại, kèm việc thống nhất tên giữa hai nguồn — lưu ý
`departments` không có UNIQUE trên `name`, sửa seed rồi chạy lại sẽ **thêm dòng mới** chứ
không cập nhật dòng cũ.

FE nhóm theo `handlingDepartment` (chuỗi). **Không** tự tạo department mới từ chuỗi.

### 3.4 `GET /api/v1/admin/staff/report`

Permission: `VIEW_REPORTS`. Query: `date_from`, `date_to`, `staff_id?`.

**Giới hạn đã biết, ghi rõ trong response:** metric tính theo `applications.assigned_to`
(hồ sơ được gán cho ai), **không phải** "ai thao tác". `audit_log.user_id` chưa đáng tin
cho mục đích này (xem 3.1). `approvalRate`/`rejectionRate` vì vậy đọc là *"kết quả của
hồ sơ được gán cho người này"*.

```typescript
interface StaffReport {
  period: { dateFrom: string; dateTo: string };
  basis: "assigned_to";                  // hằng số — FE hiện chú thích
  staff: {
    staffId: number;
    staffName: string;
    department: string | null;           // từ staff_assignments
    assigned: number;
    open: number;
    closed: number;
    overdue: number;
    avgProcessingDays: number | null;
    measurable: number;
    outcomeRates: {                      // null khi closed == 0
      approved: number | null;
      rejected: number | null;
      needsInfo: number | null;
    };
  }[];
  unassigned: { open: number; overdue: number };  // hồ sơ không thuộc ai
}
```

`unassigned` tách riêng — gộp vào một "nhân viên ảo" sẽ làm sai mọi trung bình.

### 3.5 Export

Report trả JSON; FE render `.xlsx` (SheetJS) / `.pdf` (jsPDF). BE **không** sinh file.

Permission `EXPORT_REPORTS` đã có trong [rbac.py:29](../../../src/models/rbac.py) nhưng
**không có endpoint nào dùng** — vì export nằm ở FE. Ghi lại ở đây để không ai tưởng là sót.

---

## 4. Badge System

### 4.1 Định nghĩa badge

Chép đúng từ [2026-08-25-phase-2-design.md §12.1](2026-08-25-phase-2-design.md), đổi
`id` → `badge_key` cho khớp cột DB:

| `badge_key` | Tên | Icon | Điều kiện |
|---|---|---|---|
| `first_step` | Bước đầu tiên | 🎯 | Hoàn thành 1 mục checklist |
| `half_way` | Tiến một nửa | 📊 | 50% checklist |
| `resident_card` | Thẻ cư dân | 🏠 | Hồ sơ thẻ cư dân được duyệt |
| `vehicle_card` | Thẻ xe | 🚗 | Hồ sơ thẻ xe được duyệt |
| `all_done` | Hoàn tất | 🎉 | 100% checklist |
| `fast_track` | Nhanh như chớp | ⚡ | 100% trong vòng 7 ngày kể từ onboarding |

Định nghĩa nằm trong `src/services/badges.py` dạng hằng số — **không** đưa vào DB.
Cùng lý do với rule engine checklist: tất định, đọc được trong code review.

### 4.2 Bảng `user_badges` — đã có sẵn

[migration 20260825120000:158-168](../../../alembic/versions/20260825120000_create_phase2_tables.py)
đã tạo bảng với `UNIQUE(user_id, badge_key)`. **Không cần migration mới.**

Cần thêm: ORM model `UserBadge` trong `src/models/db.py` (hiện chưa có — bảng tồn tại
nhưng không code nào chạm tới).

### 4.3 Ghi badge — chống race condition

```python
def award_badge(db: Session, user_id: int, badge_key: str) -> bool:
    """Trả True nếu badge vừa được trao, False nếu đã có.

    INSERT ... ON CONFLICT thay cho check-rồi-insert: hai request đồng thời
    (tick checklist ở hai tab) đều thấy "chưa có" rồi cùng insert, một cái vỡ
    UNIQUE. Đẩy việc phân xử xuống DB.
    """
```

SQLite (test) và Postgres đều hiểu `ON CONFLICT DO NOTHING`, nên viết được một câu SQL
chạy cả hai. Kiểm số dòng ảnh hưởng để biết có trao mới hay không.

### 4.4 Nhận diện thủ tục thẻ — dùng `category`, không dùng tên

Rev 1 định `'thẻ xe' in task_name.lower()`. Hỏng vì:

- Tên có biến thể: `"Làm thẻ cư dân (chủ hộ)"` / `"(người thuê)"`
- `"Đăng ký thẻ thang máy"`, `"Kích hoạt thẻ bể bơi"` cũng chứa chữ "thẻ"
- `checklist_item_id` **không ổn định** — `seed_data` xoá và tạo lại
  ([seed_data.py:392](../../../scripts/seed_data.py)), id đổi sau mỗi lần seed

Dùng `checklist_items.category` — ổn định qua các lần seed và đã mang đúng ngữ nghĩa:

| Badge | Điều kiện |
|---|---|
| `resident_card` | hồ sơ đạt `approved`/`delivered`, item có `category == "Giấy tờ cư dân"` |
| `vehicle_card` | hồ sơ đạt `approved`/`delivered`, item có `category == "Phương tiện"` |

**Bất biến mới:** hai chuỗi category này phải tồn tại trong seed. `seed_data` validate
lúc nạp — gõ sai thì badge im lặng không bao giờ trao, đúng lớp lỗi mà bất biến
`PROFILE_FIELDS` đang chống.

### 4.5 Điểm móc event

| Nơi | Hàm | Badge kiểm |
|---|---|---|
| `PATCH /checklist/{item_id}` ([routes.py:382](../../../src/api/routes.py)) | `check_progress_badges` | `first_step`, `half_way`, `all_done`, `fast_track` |
| `PATCH /admin/applications/{id}` ([routes.py:1003](../../../src/api/routes.py)) khi status ∈ `approved`/`delivered` | `check_card_badges` | `resident_card`, `vehicle_card` |

**Tiến độ tính lại bằng rule engine hiện có** — `_build_checklist` đã lọc checklist theo
hồ sơ cư dân. Badge dùng chung kết quả đó, không tự đếm lại: hai chỗ đếm sẽ lệch nhau.

**Untick phải xử lý:** `CompletionRequest.completed` có thể `False`. Badge đã trao
**không thu hồi** — badge ghi nhận "đã từng đạt". Quyết định này phải nêu rõ với FE.

**Lỗi badge không được làm hỏng request chính:** bọc `try/except`, log, trả checklist
như thường. Tick checklist thất bại vì lỗi gamification là đánh đổi sai.

### 4.6 `fast_track` — mốc thời gian

`users.onboarding_completed_at` ([db.py:133](../../../src/models/db.py)) — comment tại chỗ
ghi rõ *"Chỉ ghi ở lần hoàn thành onboarding ĐẦU TIÊN"*, đúng thứ cần.

`NULL` (chưa onboarding) → không xét `fast_track`, không lỗi.

7 ngày ở đây là **ngày thường**, không phải ngày làm việc — đây là mốc trải nghiệm cư dân,
không phải cam kết SLA của BQL. Khác biệt có chủ ý.

### 4.7 `GET /api/v1/user/badges`

Auth: `require_resident`.

```typescript
interface UserBadgesResponse {
  badges: {
    key: string;
    name: string;
    icon: string;
    earnedAt: string | null;
    isEarned: boolean;
  }[];   // TẤT CẢ badge, kể cả chưa đạt — FE hiện dạng khoá
  earnedCount: number;
  totalCount: number;
}
```

**Bỏ `newlyEarned` của rev 1.** Trường đó không có nghĩa trong một GET không trạng thái.
Muốn hiệu ứng chúc mừng thì `PATCH /checklist/{item_id}` trả thêm
`newlyEarnedBadges: string[]` — đúng chỗ biết được "vừa mới".

`ChecklistResponse` cần thêm trường này. Vì FE cũ bỏ qua trường lạ, đây là thay đổi
tương thích ngược.

---

## 5. Settings API

### 5.1 Phạm vi v1 — chỉ những gì có nơi tiêu thụ

Rev 1 đưa `sla.defaultProcessingDays` vào settings. **Bỏ**: SLA nằm ở từng thủ tục
(`sla_business_days`), một giá trị mặc định toàn cục không được code nào đọc là dead config.

Settings v1 chỉ giữ những khoá **thực sự có nơi dùng**:

```json
{
  "reports": {
    "overdueWarningDays": 2,
    "defaultPeriodDays": 30
  }
}
```

- `overdueWarningDays` — số ngày làm việc trước hạn thì hồ sơ vào diện "sắp trễ" ở report.
- `defaultPeriodDays` — kỳ mặc định khi FE không truyền `date_from`/`date_to`.

Cả hai đều được đọc trong report query. Không thêm khoá nào chưa có nơi tiêu thụ.

### 5.2 Endpoints

| Method | Endpoint | Permission |
|---|---|---|
| GET | `/api/v1/admin/settings` | `MANAGE_SETTINGS` |
| PATCH | `/api/v1/admin/settings` | `MANAGE_SETTINGS` |

`GET` trả settings đã merge với mặc định trong code — DB rỗng vẫn trả đủ khoá, không 404.
Mặc định là hằng số trong `src/services/settings.py`; DB chỉ lưu **phần đã bị đổi**.

`PATCH` nhận partial, validate qua Pydantic:
- `overdueWarningDays`: 1–10
- `defaultPeriodDays`: 7–365
- Khoá lạ → 422, **không** im lặng bỏ qua.

Mỗi lần PATCH ghi `audit_log` (`action = "settings.updated"`) — dùng `log_action` sẵn có.

### 5.3 Staff/Department management — KHÔNG thuộc phạm vi này

Câu hỏi của FE: *"Staff/Department management dùng API nào?"*

Trả lời: **không dùng Settings API.** Permission đã tách sẵn trong
[rbac.py:33](../../../src/models/rbac.py): `MANAGE_DEPARTMENTS` ≠ `MANAGE_SETTINGS`.
Gộp vào một endpoint sẽ phá ranh giới phân quyền đó.

CRUD department/staff cần spec riêng (bảng `departments`, `staff_assignments` đã tồn tại
nhưng chưa có endpoint quản trị). **Ngoài phạm vi tài liệu này** — cần chốt riêng.

---

## 6. Tổng hợp endpoint mới

| Method | Endpoint | Permission |
|---|---|---|
| GET | `/api/v1/admin/applications/report` | `VIEW_REPORTS` |
| GET | `/api/v1/admin/departments/report` | `VIEW_REPORTS` |
| GET | `/api/v1/admin/staff/report` | `VIEW_REPORTS` |
| GET | `/api/v1/admin/settings` | `MANAGE_SETTINGS` |
| PATCH | `/api/v1/admin/settings` | `MANAGE_SETTINGS` |
| GET | `/api/v1/user/badges` | `require_resident` |

Sửa đổi endpoint có sẵn: `PATCH /api/v1/checklist/{item_id}` trả thêm `newlyEarnedBadges`.

---

## 7. Thứ tự triển khai

| # | Việc | Verify |
|---|---|---|
| 1 | Migration: `sla_business_days`, `system_settings`, index `audit_log` | `alembic upgrade head` rồi `downgrade` sạch |
| 2 | Seed `sla_business_days` + validate bất biến `third_party_info ⟹ NULL` | `python -m scripts.seed_data` pass; sửa 1 giá trị sai → seed từ chối |
| 3 | `business_days_between()` trong `src/services/reporting.py` | Unit test: qua cuối tuần, cùng ngày, ngược thứ tự |
| 4 | Truy vấn mốc từ `audit_log` | Test: hồ sơ quay lại `processing` sau `needs_info` vẫn lấy mốc **đầu** |
| 5 | 3 report endpoints | Test permission + kỳ rỗng trả `null` (không phải `0`) |
| 6 | `src/services/settings.py` + GET/PATCH | Test: DB rỗng trả mặc định; khoá lạ → 422 |
| 7 | ORM `UserBadge` + `award_badge` ON CONFLICT | Test: gọi 2 lần chỉ trao 1 |
| 8 | `src/services/badges.py` + móc 2 event | Test: tick đủ 100% → `all_done`; untick không thu hồi |
| 9 | `GET /user/badges` + `newlyEarnedBadges` | Test: trả đủ 6 badge kể cả chưa đạt |

Test dùng SQLite in-memory + `StaticPool`, fixture `fake_auth_provisioning`, **không gọi
dịch vụ ngoài** (bẫy #5 trong CLAUDE.md).

---

## 8. Ngoài phạm vi

- **Ngày lễ** trong tính ngày làm việc — chưa có nguồn dữ liệu, bịa là tự đặt số liệu.
- **Staff/Department CRUD** — cần spec riêng (mục 5.3).
- **Sinh file Excel/PDF ở BE** — FE render.
- **Caching** — không có cơ sở ở quy mô hiện tại (mục 1.3).
- **Backfill mốc thời gian cho hồ sơ trước Phase 2** — báo qua `coverage` thay vì đoán.
- **Badge UI** — vai FE.

---

## 9. Câu cần team chốt trước khi code

1. **Cận trên của khoảng SLA** (mục 2.2) — `"1–3 ngày"` → `3`. Đúng ý BQL chưa, hay muốn cận dưới?
2. **`rejected` tính vào `avgProcessingDays`** (mục 3.2) — hay chỉ tính hồ sơ được duyệt?
3. **Staff report theo `assigned_to`** (mục 3.4) — chấp nhận giới hạn này, hay cần sửa
   `performed_by` cho đủ đường ghi audit trước?
4. **Badge không thu hồi khi untick** (mục 4.5) — xác nhận với FE.

---

## 10. Khác biệt phát sinh lúc triển khai (30/08)

Bốn chỗ code làm khác spec. Ghi lại ở đây vì đều là quyết định, không phải chi tiết vặt:

**1. `MANAGE_SETTINGS` được thêm vào role `admin`.**
Quyền này trước chỉ thuộc `super_admin`, nhưng `ROLES` trong
[db.py:48](../../../src/models/db.py) chỉ có `("resident", "admin")` — không tài khoản nào
mang được vai `super_admin`, nên GET/PATCH `/admin/settings` **không ai gọi nổi**.
Hai test trong `tests/test_rbac.py` chốt cứng chủ ý cũ nên đã sửa theo.
`MANAGE_USERS`, `MANAGE_DEPARTMENTS`, `AUDIT_LOG` vẫn nằm ngoài tầm `admin`.

**2. Danh sách quá hạn KHÔNG lọc theo kỳ báo cáo.**
Spec mục 3.2 ngầm hiểu mọi số liệu đều trong kỳ. Sai với `overdue`: "quá hạn" là tình
trạng **hiện tại**, không phải sự kiện trong kỳ. Hồ sơ nộp ba tháng trước mà vẫn treo là
thứ BQL cần thấy nhất, mà lọc theo kỳ 30 ngày sẽ giấu đúng nó — càng tồn đọng lâu càng
chắc chắn bị giấu. `_load_open_applications()` quét mọi hồ sơ chưa đóng.

**3. `date_from=` rỗng được hiểu là "không chọn", không phải lỗi.**
Giao diện gửi chuỗi rỗng khi người dùng xoá ô lọc. Trả 422 vào mặt họ vì đúng thao tác đó
là vô lý. Chuỗi **có nội dung** mà sai định dạng vẫn nổ như cũ.

**4. `trends[]` chỉ có dòng cho ngày CÓ dữ liệu.**
Kỳ 365 ngày sẽ sinh 365 dòng mà phần lớn là số 0. Biểu đồ phía FE tự điền khoảng trống.

**Thêm hai ORM model ngoài kế hoạch:** `AuditLog` và `UserBadge`. Cả hai bảng đã có
trong migration Phase 2 nhưng không có model, nên `Base.metadata.create_all` trong test
không dựng chúng — `log_action` nuốt lỗi "no such table" và test report không có gì để đọc.

**Chưa verify được trên Postgres:** hai migration Phase 2 có sẵn
(`0fa843848af8`, `20260825120000`) dùng `information_schema` nên `alembic upgrade head`
không chạy hết trên SQLite. Migration mới đã test riêng (up + down) trên schema dựng từ
ORM; **cần chạy thật trên Supabase trước khi deploy**.

---

**Trạng thái:** rev 2 — đã triển khai, chờ review
