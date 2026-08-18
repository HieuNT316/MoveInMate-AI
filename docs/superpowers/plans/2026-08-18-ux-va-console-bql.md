# Kế hoạch triển khai — Trải nghiệm người dùng & Console Ban quản lý

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Làm ứng dụng dùng được trên điện thoại đúng như manifest đang tuyên bố, cho Ban quản lý một console có chiều sâu (xem và thao tác trên từng cư dân, tự nạp tài liệu vào tri thức trợ lý), và trả nốt các guardrail đã khai với BTC — tất cả trong 14 ngày trước Demo Day 01/09.

**Architecture:** Backend FastAPI + SQLAlchemy giữ nguyên kiến trúc hiện tại; endpoint mới ghép lại các schema đã có thay vì bịa schema phẳng, tận dụng `_build_checklist` sẵn có. Frontend Next.js App Router sửa ở **lớp vỏ dùng chung** (`Layout`/`Sidebar`/`Header`) nên 15 trang cùng hết lỗi trong một lần sửa, thay vì vá từng trang. Chroma chuyển từ đĩa container tạm sang Railway Volume có seed lúc khởi động.

**Tech Stack:** Python 3.11 · FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · pytest + pytest-asyncio + httpx · Supabase (Postgres session pooler, Auth Admin API, Storage private bucket) · Chroma + LangChain · Next.js App Router + TypeScript + Tailwind · Railway (backend) + Vercel (frontend)

**Spec:** `docs/superpowers/specs/2026-08-18-ux-va-console-bql-design.md`

## Global Constraints

Mọi task đều mang theo các ràng buộc này. Không lặp lại ở từng task.

- **Không in secret ra stdout.** `DATABASE_URL` chứa mật khẩu — dùng `safe_database_url()`. Repo có hook đẩy log lên server chấm điểm.
- **`DATABASE_URL` trong `.env` trỏ vào Supabase production thật.** Không chạy `seed_data` hay `alembic upgrade` lên nó trong lúc phát triển.
- **Test không được gọi dịch vụ ngoài.** Fixture `fake_auth_provisioning` và `fake_storage`. Test chạy SQLite in-memory với `StaticPool`.
- **Không PATCH hồ sơ tài khoản demo** — dữ liệu seed là tất định để cả nhóm thấy giống nhau.
- **Giấy tờ tuỳ thân không bao giờ embed vào Chroma.** Bucket private, URL ký sống 5 phút, không ghi URL ra log. Demo dùng ảnh giả hoặc đã che số.
- **`SUPABASE_SERVICE_KEY` chỉ dùng ở backend** — nó bỏ qua toàn bộ RLS.
- **`X-User-Id` chỉ là lối dev**, bị chặn khi `APP_ENV=production`.
- **Định tuyến hồ sơ và phân loại cư dân dùng rule-based, không LLM.**
- **`sources[]` sinh tất định từ `rag_retrieve`**; guard chống bịa nằm trong code, không trong prompt.
- **`data/chroma/` là DB nhị phân trong git.** Chỉ vai AI chạy `ingest_kb`. Chỉ *đọc* Chroma cũng làm bẩn `.bin`/`.sqlite3` → `git checkout -- data/chroma/` để dọn, **nhưng không bao giờ ngay sau khi ingest**. Sau mọi thao tác git đụng thư mục này, kiểm `collection.count()`.
- **Alembic:** trên bảng đã có dữ liệu, luôn **thêm nullable → backfill → mới khoá NOT NULL**. Autogenerate sinh thẳng `nullable=False` và luôn vỡ.
- **Lệnh `railway` phải chạy từ PowerShell.** `railway up` đóng gói *thư mục hiện tại*, không phải commit — `git status` trước.
- Trên Windows, tiếng Việt trong stdout cần `PYTHONIOENCODING=utf-8`.
- `ruff check --fix scripts/` sẽ sửa cả script logging của BTC — chỉ chạy trên file mình sửa.
- **Trước mỗi commit:** `ruff check src/ tests/ && pytest -q`, rồi `git status` để chắc không commit thứ ngoài phạm vi.

---

## Cấu trúc file

**Backend — tạo mới**

| File | Trách nhiệm |
|---|---|
| `alembic/versions/<rev>_add_account_status.py` | Cột `account_status` trên `users` |
| `alembic/versions/<rev>_add_embed_status.py` | Cột `embed_status` trên `documents` |
| `src/services/chroma_seed.py` | Chép KB từ `chroma_seed` sang volume rỗng lúc khởi động |

**Backend — sửa**

| File | Sửa gì |
|---|---|
| `src/models/db.py` | `User.account_status`, `Document.embed_status` |
| `src/models/schemas.py` | `AccountStatus`, `ResidentDetailResponse`, `AttachmentUrlResponse`, `AccountStatusUpdateRequest`, `TemporaryPasswordResponse`, `DocumentIngestRequest`, `DocumentResponse`; thêm `account_status` vào `ResidentProgress` |
| `src/api/routes.py` | 6 endpoint mới |
| `src/api/deps.py` | Chặn tài khoản `locked` trong `get_current_user` |
| `src/services/store.py` | `_attachment_dict` thôi ký URL; thêm `get_attachment`, `set_account_status`, `create_document_record`, `set_embed_status` |
| `src/services/supabase_admin.py` | `update_auth_password()` |
| `src/main.py` | Gọi seed lúc khởi động; endpoint `/health/deep` |
| `tests/conftest.py` | `fake_auth_provisioning` → `autouse`, chặn thêm `update_auth_password` |
| `Dockerfile` | Chép KB đã ingest vào `/app/data/chroma_seed` |

**Frontend — tạo mới**

| File | Trách nhiệm |
|---|---|
| `web/app/lib/nav.ts` | Nguồn duy nhất của hai mảng menu |
| `web/app/components/MobileTabBar.tsx` | Thanh tab đáy, ẩn từ `lg` trở lên |
| `web/app/components/Toast.tsx` | `ToastProvider` + `useToast` |
| `web/app/components/EmptyState.tsx` | Khối "chưa có gì" dùng chung |
| `web/app/components/ErrorState.tsx` | Khối lỗi dùng chung |

**Frontend — sửa:** `Sidebar.tsx` · `BQLSidebar.tsx` · `Layout.tsx` · `BQLLayout.tsx` · `Header.tsx` · `ChatWidget.tsx` · `chat/page.tsx` · `dashboard/page.tsx` · `checklist/page.tsx` · `app/layout.tsx` · `lib/api.ts`

**Tài liệu:** `docs/CONTRACT_US13.md` · `docs/ROLES_AND_PLAN.md` · `docs/PROJECT_CHARTER.md` · `docs/architecture_diagram.md` · `docs/DEPLOY.md` · `README.md` · `.env.example`

---

# Giai đoạn A — Hợp đồng và lớp vỏ (18–19/08)

## Task 1: Chốt đổi hợp đồng ký-URL-theo-yêu-cầu

Đi trước mọi thứ khác. Không phải vì khó mà vì Thu cần thời gian dài nhất để phản ứng — charter mục 12 bắt chốt bằng văn bản trước khi hai vai code song song.

**Files:**
- Modify: `docs/CONTRACT_US13.md` (mục 7, quanh dòng 160–232)

**Interfaces:**
- Produces: hợp đồng mà Task 2, Task 3 và phần frontend của Thu cùng bám theo.

- [ ] **Step 1: Sửa khối phản hồi 201 của `POST /applications/{id}/attachments`**

Đổi dòng `url` trong ví dụ JSON thành:

```jsonc
  "url": null,   // LUÔN null từ 18/08 — xem mục "Lấy link xem ảnh" bên dưới
```

- [ ] **Step 2: Thêm mục mới ngay sau khối đó**

```markdown
### Lấy link xem ảnh — đổi từ 18/08

`url` trong mọi phản hồi danh sách **luôn là `null`**. Muốn xem một tệp thì gọi
riêng:

`GET /api/v1/applications/{application_id}/attachments/{attachment_id}/url`

```jsonc
// nhận 200
{ "url": "https://…/object/sign/…" }   // hết hạn sau 5 phút
```

Lỗi: **404** tệp không tồn tại, không thuộc hồ sơ đó, hoặc hồ sơ không phải của
mình. BQL gọi được mọi tệp.

**Vì sao đổi:** ký URL là một lời gọi mạng đồng bộ tới Supabase, chạy một lần
cho **mỗi tệp, mỗi lần đọc hồ sơ**, bên trong route `async`. Nó chặn event loop
nên mọi request của mọi người khác đều phải đợi. Ký khi thật sự mở ảnh đưa số
lượt gọi từ N xuống thường là 0.

**Cách sửa phía giao diện:** gọi endpoint này khi người dùng bấm mở ảnh, đừng
gọi sẵn cho cả danh sách — làm thế là quay lại đúng vấn đề vừa sửa.
```

- [ ] **Step 3: Commit và nhắn Thu**

```bash
git add docs/CONTRACT_US13.md
git commit -m "docs: ký URL đính kèm theo yêu cầu thay vì mỗi lần đọc hồ sơ"
```

Nhắn Thu nội dung: `attachment.url` từ nay luôn `null` trong danh sách; gọi endpoint mới khi mở ảnh; backend giữ trường `url` trong schema nên trang **không vỡ**, chỉ là ảnh không hiện cho tới khi FE đổi.

---

## Task 2: Endpoint ký URL theo yêu cầu

**Files:**
- Modify: `src/models/schemas.py`
- Modify: `src/services/store.py`
- Modify: `src/api/routes.py`
- Test: `tests/test_api/test_routes.py`

**Interfaces:**
- Consumes: hợp đồng ở Task 1.
- Produces: `GET /api/v1/applications/{application_id}/attachments/{attachment_id}/url` → `{"url": str}`; hàm `store.get_attachment(db, application_id, attachment_id) -> ApplicationAttachment | None`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `tests/test_api/test_routes.py`, ngay sau nhóm test gán loại giấy tờ:

```python
# --- Ký URL theo yêu cầu (18/08) ----------------------------------------


@pytest.mark.asyncio
async def test_chu_ho_so_lay_duoc_link_xem_anh(client):
    app = await _create(client, CAR_CARD_ITEM)
    aid = app["application_id"]
    att_id = (await _upload(client, aid)).json()["attachment_id"]

    r = await client.get(
        f"/api/v1/applications/{aid}/attachments/{att_id}/url", headers=OWNER
    )
    assert r.status_code == 200
    assert r.json()["url"].startswith("https://")


@pytest.mark.asyncio
async def test_bql_lay_duoc_link_cua_moi_ho_so(client):
    app = await _create(client, CAR_CARD_ITEM)
    aid = app["application_id"]
    att_id = (await _upload(client, aid)).json()["attachment_id"]

    r = await client.get(
        f"/api/v1/applications/{aid}/attachments/{att_id}/url", headers=ADMIN
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_cu_dan_khac_khong_lay_duoc_link(client):
    app = await _create(client, CAR_CARD_ITEM)
    aid = app["application_id"]
    att_id = (await _upload(client, aid)).json()["attachment_id"]

    r = await client.get(
        f"/api/v1/applications/{aid}/attachments/{att_id}/url", headers=RENTER
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_id_tep_cua_ho_so_khac_tra_404(client):
    """Không kiểm cặp (hồ sơ, tệp) thì đoán được id tệp là đọc được ảnh CCCD
    của người khác. Đúng lỗi bản review D1 đã bắt ở endpoint gán loại."""
    first = await _create(client, CAR_CARD_ITEM)
    second = await _create(client, RESIDENT_CARD_ITEM)
    att_id = (await _upload(client, first["application_id"])).json()["attachment_id"]

    r = await client.get(
        f"/api/v1/applications/{second['application_id']}/attachments/{att_id}/url",
        headers=OWNER,
    )
    assert r.status_code == 404
```

Nếu hằng `RESIDENT_CARD_ITEM` chưa tồn tại, khai cạnh `CAR_CARD_ITEM` bằng id của một mục checklist khác **cũng thuộc checklist chủ hộ** (xem `scripts/seed_data.py`, mảng `CHECKLIST_ITEMS`).

- [ ] **Step 2: Chạy test cho chắc là hỏng**

Run: `pytest tests/test_api/test_routes.py -k lay_duoc_link -v`
Expected: FAIL — 404 vì route chưa tồn tại.

- [ ] **Step 3: Thêm schema**

Trong `src/models/schemas.py`, sau `AttachmentResponse`:

```python
class AttachmentUrlResponse(BaseModel):
    """Link đọc tạm thời, ký khi người dùng thật sự mở ảnh.

    Tách khỏi phản hồi danh sách vì ký là một lời gọi mạng đồng bộ tới Supabase:
    ký sẵn cho mọi tệp mỗi lần đọc hồ sơ sẽ chặn event loop.
    """

    url: str
```

- [ ] **Step 4: Thêm hàm tra cứu vào store**

Trong `src/services/store.py`, cạnh `get_application`:

```python
def get_attachment(
    db: Session, application_id: int, attachment_id: int
) -> ApplicationAttachment | None:
    """Tệp đính kèm, tra theo CẢ HAI khoá.

    Thiếu điều kiện `application_id` thì đoán được id tệp là đọc được ảnh giấy
    tờ của người khác — quyền phải kiểm trên cặp, không phải trên một id.
    """
    return db.scalar(
        select(ApplicationAttachment).where(
            ApplicationAttachment.attachment_id == attachment_id,
            ApplicationAttachment.application_id == application_id,
        )
    )
```

- [ ] **Step 5: Thêm route**

Trong `src/api/routes.py`, sau `PATCH /admin/applications/{id}/attachments/{aid}`:

```python
@router.get(
    "/applications/{application_id}/attachments/{attachment_id}/url",
    response_model=AttachmentUrlResponse,
)
async def get_attachment_url(
    application_id: int,
    attachment_id: int,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttachmentUrlResponse:
    """Ký link đọc ảnh, chỉ khi người dùng thật sự mở nó.

    Dùng `get_current_user` chứ KHÔNG phải `require_resident`: BQL cần xem đúng
    những ảnh này để đối chiếu giấy tờ. Quyền kiểm trong thân hàm.
    """
    attachment = store.get_attachment(db, application_id, attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tệp này."
        )

    app = store.get_application(db, application_id)
    if app is None or (user["role"] != "admin" and app.user_id != user["user_id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tệp này."
        )

    url = storage.signed_url(attachment.storage_path)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Không ký được link xem ảnh.",
        )
    return AttachmentUrlResponse(url=url)
```

Thêm `get_current_user` vào import từ `src.api.deps`, `AttachmentUrlResponse` vào import schemas, và `from src.services import storage` nếu chưa có.

- [ ] **Step 6: Chạy test cho chắc là xanh**

Run: `pytest tests/test_api/test_routes.py -k "lay_duoc_link or ho_so_khac_tra_404" -v`
Expected: PASS, 4 test.

- [ ] **Step 7: Commit**

```bash
ruff check src/ tests/ && pytest -q
git add src/models/schemas.py src/services/store.py src/api/routes.py tests/test_api/test_routes.py
git commit -m "feat: ký link xem ảnh khi mở, không phải mỗi lần đọc hồ sơ"
```

---

## Task 3: Thôi ký URL trong phản hồi danh sách

Tách khỏi Task 2 có chủ đích: endpoint mới phải tồn tại trước khi bỏ đường cũ, nếu không sẽ có một nhịp không ai xem được ảnh.

**Files:**
- Modify: `src/services/store.py:294-311` (`_attachment_dict`)
- Test: `tests/test_api/test_routes.py`

**Interfaces:**
- Consumes: `GET .../url` từ Task 2.
- Produces: `AttachmentResponse.url` luôn `None` ở mọi phản hồi danh sách.

- [ ] **Step 1: Sửa test đang khẳng định điều ngược lại**

`tests/test_api/test_routes.py:1002` hiện có `assert row["attachments"][0]["url"]`. Đổi thành:

```python
    # Từ 18/08 danh sách không ký URL nữa — xem GET .../attachments/{id}/url.
    assert row["attachments"][0]["url"] is None
```

- [ ] **Step 2: Thêm test khoá hành vi mới**

```python
@pytest.mark.asyncio
async def test_danh_sach_ho_so_khong_ky_url(client):
    """Ký ở đây là một lời gọi mạng đồng bộ cho MỖI tệp, chặn event loop."""
    app = await _create(client, CAR_CARD_ITEM)
    await _upload(client, app["application_id"])

    mine = (await client.get("/api/v1/applications", headers=OWNER)).json()[0]
    assert mine["attachments"][0]["url"] is None
```

- [ ] **Step 3: Chạy test cho chắc là hỏng**

Run: `pytest tests/test_api/test_routes.py -k khong_ky_url -v`
Expected: FAIL — `url` đang là `https://fake.test/...` do fixture `fake_storage`.

- [ ] **Step 4: Bỏ lời gọi ký**

Trong `src/services/store.py`, `_attachment_dict`:

```python
def _attachment_dict(att: ApplicationAttachment) -> dict[str, Any]:
    """Metadata tệp. `url` LUÔN None ở đây — ký theo yêu cầu (18/08).

    Trước đó mỗi tệp được ký ngay lúc đọc hồ sơ: một `httpx.post` ĐỒNG BỘ tới
    Supabase, bên trong route `async`, một lần cho mỗi tệp. Vừa tuần tự vừa
    chặn event loop nên mọi request của mọi người khác đều phải đợi.

    Giữ lại trường thay vì xoá hẳn để giao diện chưa kịp đổi không vỡ vì thiếu
    khoá — ảnh không hiện thì tốt hơn trang trắng.
    """
    return {
        "attachment_id": att.attachment_id,
        "filename": att.filename,
        "document_type": att.document_type,
        "content_type": att.content_type,
        "size_bytes": att.size_bytes,
        "url": None,
        "uploaded_at": _as_utc(att.uploaded_at),
    }
```

- [ ] **Step 5: Chạy toàn bộ test**

Run: `pytest -q`
Expected: PASS. Nếu có test khác đỏ vì khẳng định `url` có giá trị, sửa chúng theo cùng lý do — đừng khôi phục lời gọi ký.

- [ ] **Step 6: Commit**

```bash
ruff check src/ tests/ && pytest -q
git add src/services/store.py tests/test_api/test_routes.py
git commit -m "perf: bỏ ký URL đồng bộ cho từng tệp trong mỗi lần đọc hồ sơ"
```

---

## Task 4: Nguồn menu dùng chung + thanh tab đáy

**Files:**
- Create: `web/app/lib/nav.ts`
- Create: `web/app/components/MobileTabBar.tsx`
- Modify: `web/app/components/Sidebar.tsx:21-26`, `web/app/components/BQLSidebar.tsx:30-33`

**Interfaces:**
- Produces: `RESIDENT_NAV` và `BQL_NAV` kiểu `NavItem[]`; component `<MobileTabBar items={…} />`. Task 5 dùng cả hai.

- [ ] **Step 1: Tạo nguồn menu duy nhất**

`web/app/lib/nav.ts`:

```ts
import {
  Bot,
  ClipboardList,
  Inbox,
  LayoutDashboard,
  Users,
  UserRound,
  FileText,
  type LucideIcon,
} from "lucide-react";

/**
 * Nguồn DUY NHẤT của menu điều hướng. Sidebar (desktop) và MobileTabBar
 * (mobile) cùng đọc từ đây.
 *
 * Nếu mỗi bên tự giữ một bản danh sách, sớm muộn chúng lệch nhau — đúng cái
 * bẫy REQUIRED_DOCUMENTS vừa dẹp xong hồi 18/08.
 */
export type NavItem = { title: string; icon: LucideIcon; href: string };

export const RESIDENT_NAV: NavItem[] = [
  { title: "Tổng quan", icon: LayoutDashboard, href: "/dashboard" },
  { title: "AI Chat", icon: Bot, href: "/chat" },
  { title: "Checklist", icon: ClipboardList, href: "/checklist" },
  { title: "Hồ sơ", icon: UserRound, href: "/profile" },
];

export const BQL_NAV: NavItem[] = [
  { title: "Tổng quan", icon: LayoutDashboard, href: "/bql/dashboard" },
  { title: "Yêu cầu", icon: Inbox, href: "/bql/applications" },
  { title: "Cư dân", icon: Users, href: "/bql/residents" },
  { title: "Tài liệu", icon: FileText, href: "/bql/documents" },
];
```

Nhan đề `Checklist` ngắn hơn `Checklist & Tiến độ` vì thanh tab chỉ rộng bằng một phần tư màn hình. Sidebar desktop dùng chung mảng này nên nhãn đổi ở cả hai — chấp nhận, đổi lại là không bao giờ lệch.

- [ ] **Step 2: Tạo thanh tab**

`web/app/components/MobileTabBar.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { NavItem } from "../lib/nav";

/**
 * Điều hướng cho màn hình nhỏ. Ẩn từ `lg` trở lên, nơi sidebar tiếp quản.
 *
 * Chọn thanh tab thay vì drawer + hamburger vì cả hai khu chỉ có 4 mục: bốn
 * mục vừa khít một thanh, nên không cần lớp phủ và không cần trạng thái
 * đóng/mở. Với PWA khai `display: standalone`, đây cũng là thứ khiến sản phẩm
 * đọc ra như một app thay vì một trang web bị bóp lại.
 */
export default function MobileTabBar({ items }: { items: NavItem[] }) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Điều hướng chính"
      className="fixed inset-x-0 bottom-0 z-40 flex border-t border-border bg-surface pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      {items.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] ${
              active ? "text-gold" : "text-muted"
            }`}
          >
            <Icon className="h-5 w-5" strokeWidth={active ? 2 : 1.75} />
            <span className={active ? "font-medium" : ""}>{item.title}</span>
          </Link>
        );
      })}
    </nav>
  );
}
```

`pb-[env(safe-area-inset-bottom)]` là để thanh tab không nằm dưới vạch home của iPhone.

- [ ] **Step 3: Cho hai sidebar dùng nguồn chung**

Trong `web/app/components/Sidebar.tsx`, xoá mảng `menus` cục bộ và các import icon nay không còn dùng, thay bằng:

```tsx
import { RESIDENT_NAV } from "../lib/nav";
```

rồi đổi `menus.map(` thành `RESIDENT_NAV.map(`. Làm y hệt cho `BQLSidebar.tsx` với `BQL_NAV`.

Ở `BQLSidebar.tsx` **xoá luôn khối `comingSoon` và phần render nó** (`Sắp có`, hai mục xám khoá). `BQL_NAV` nay có đủ bốn mục thật; giữ ổ khoá bên cạnh mục thật là để lại đúng ấn tượng "bản nháp" mà mentor đã nói. Xoá cả import `Lock`, `ClipboardCheck`, `Bot` nếu không còn chỗ nào dùng.

- [ ] **Step 4: Kiểm biên dịch**

Run: `cd web && npx tsc --noEmit`
Expected: không lỗi. Nếu báo import thừa, xoá đúng import đó — đó là rác do chính bước này tạo ra.

- [ ] **Step 5: Commit**

```bash
git add web/app/lib/nav.ts web/app/components/MobileTabBar.tsx web/app/components/Sidebar.tsx web/app/components/BQLSidebar.tsx
git commit -m "feat(web): một nguồn menu duy nhất và thanh tab cho màn hình nhỏ"
```

⚠️ Sau bước này **`/bql/residents` và `/bql/documents` chưa tồn tại** — menu sẽ trỏ tới 404 cho tới Task 20/21. Chấp nhận trong nhánh làm việc; **không deploy** cho tới khi hai trang đó có mặt.

---

## Task 5: Vỏ layout responsive

**Files:**
- Modify: `web/app/components/Sidebar.tsx:47`, `web/app/components/BQLSidebar.tsx:58`
- Modify: `web/app/components/Layout.tsx`, `web/app/components/BQLLayout.tsx`

**Interfaces:**
- Consumes: `MobileTabBar`, `RESIDENT_NAV`, `BQL_NAV` từ Task 4.

- [ ] **Step 1: Ẩn sidebar dưới `lg`**

`Sidebar.tsx:47` — đổi `className` của `<aside>`:

```tsx
    <aside className="hidden lg:flex w-72 shrink-0 bg-surface text-ink h-screen flex-col overflow-y-auto border-r border-border">
```

`BQLSidebar.tsx:58`:

```tsx
    <aside className="hidden lg:flex h-screen w-72 shrink-0 flex-col overflow-y-auto border-r border-[#E2E8F0] bg-white text-[#1E293B]">
```

Lưu ý cả hai: `flex` đã nằm trong `lg:flex` nên bỏ chữ `flex` đứng một mình, giữ `flex-col`.

- [ ] **Step 2: Gắn thanh tab vào layout cư dân**

`web/app/components/Layout.tsx`:

```tsx
import Sidebar from "./Sidebar";
import Header from "./Header";
import ChatWidget from "./ChatWidget";
import MobileTabBar from "./MobileTabBar";
import { RESIDENT_NAV } from "../lib/nav";

export default function Layout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-[100dvh] overflow-hidden bg-background">
      <Sidebar />

      <div className="flex-1 min-w-0 overflow-y-auto">
        <Header />

        <main className="mx-auto max-w-6xl px-4 py-6 pb-24 lg:px-8 lg:py-10 lg:pb-10">
          {children}
        </main>
      </div>

      <ChatWidget />
      <MobileTabBar items={RESIDENT_NAV} />
    </div>
  );
}
```

`h-screen` → `h-[100dvh]`: trên mobile `100vh` không trừ thanh địa chỉ trình duyệt nên đáy trang bị cắt.

- [ ] **Step 3: Làm y hệt cho layout BQL**

`web/app/components/BQLLayout.tsx`:

```tsx
import BQLSidebar from "./BQLSidebar";
import Header from "./Header";
import MobileTabBar from "./MobileTabBar";
import { BQL_NAV } from "../lib/nav";

export default function BQLLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-[100dvh] overflow-hidden bg-[#F8FAFC]">
      <BQLSidebar />

      <div className="flex-1 min-w-0 overflow-y-auto">
        <Header />

        <main className="mx-auto max-w-6xl px-4 py-6 pb-24 lg:px-8 lg:py-10 lg:pb-10">
          {children}
        </main>
      </div>

      <MobileTabBar items={BQL_NAV} />
    </div>
  );
}
```

- [ ] **Step 4: Kiểm bằng mắt**

Run: `cd web && npx tsc --noEmit && npm run dev`

Mở DevTools ở **390px** và kiểm: sidebar không còn chiếm chỗ · thanh tab hiện ở đáy · nội dung không bị thanh tab che (kéo xuống cuối trang) · ở **1280px** thanh tab biến mất và sidebar trở lại như cũ.

- [ ] **Step 5: Commit**

```bash
git add web/app/components/Sidebar.tsx web/app/components/BQLSidebar.tsx web/app/components/Layout.tsx web/app/components/BQLLayout.tsx
git commit -m "feat(web): vỏ layout dùng được trên điện thoại"
```

---

## Task 6: Những chỗ còn tràn trên màn hình nhỏ

**Files:**
- Modify: `web/app/components/Header.tsx`, `web/app/components/ChatWidget.tsx:86`
- Modify: `web/app/chat/page.tsx:191,401`, `web/app/dashboard/page.tsx:199`

- [ ] **Step 1: Thu gọn Header**

Trong `Header.tsx`, đổi thẻ `<header>` và khối tiêu đề:

```tsx
    <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-border bg-surface/90 px-4 backdrop-blur lg:h-20 lg:px-8">
      <div className="min-w-0">
        <h2 className="truncate font-display text-lg font-semibold text-ink lg:text-2xl">
          {current.title}
        </h2>
        {current.subtitle && (
          <p className="hidden text-sm text-muted lg:block">{current.subtitle}</p>
        )}
      </div>
```

Tiêu đề BQL dài (`"MoveInMate AI — Bảng điều khiển Ban Quản Lý"`) nên cần `truncate` + `min-w-0`, nếu không nó đẩy nút bên phải ra khỏi màn hình.

- [ ] **Step 2: Ẩn nút chat nổi trên mobile**

`ChatWidget.tsx:86`:

```tsx
    <div className="fixed bottom-6 right-6 z-50 hidden lg:block">
```

Ẩn hẳn chứ không đẩy lên `bottom-24`: thanh tab đã có mục "AI Chat", để cả hai là hai lối vào cùng một chỗ nằm cạnh nhau.

- [ ] **Step 3: Sửa trang chat**

`chat/page.tsx:401` — panel danh sách hội thoại:

```tsx
    <div className="hidden w-64 shrink-0 flex-col overflow-hidden rounded-2xl border border-border bg-surface lg:flex">
```

`chat/page.tsx:191` — khung tin nhắn:

```tsx
      <div className="flex h-[calc(100dvh-13rem)] min-w-0 flex-1 flex-col overflow-hidden rounded-2xl border border-border bg-surface lg:h-[calc(100vh-9rem)]">
```

`13rem` trên mobile = header 4rem + padding main 1.5rem×2 + thanh tab ~6rem.

Và khối gợi ý ở dòng 320, `grid-cols-2` quá chật ở 390px:

```tsx
              <div className="grid grid-cols-1 gap-2 pt-1 sm:grid-cols-2">
```

- [ ] **Step 4: Cho bảng cuộn ngang**

`dashboard/page.tsx:199` — bọc `<table>`:

```tsx
        <div className="overflow-x-auto">
          <table className="w-full min-w-[32rem] text-sm">
```

Nhớ đóng thêm một `</div>` sau `</table>`.

- [ ] **Step 5: Kiểm bằng mắt**

Run: `cd web && npx tsc --noEmit && npm run build`

Ở **390px** kiểm từng trang `/dashboard` · `/chat` · `/checklist` · `/profile` · `/bql/dashboard` · `/bql/applications`: **không trang nào cuộn ngang được** ở cấp body. Đây là phép thử chính; bảng cuộn trong khung của nó thì đúng, cả trang trôi ngang là sai.

- [ ] **Step 6: Commit**

```bash
git add web/app/components/Header.tsx web/app/components/ChatWidget.tsx web/app/chat/page.tsx web/app/dashboard/page.tsx
git commit -m "fix(web): những chỗ còn tràn ngang trên màn hình nhỏ"
```

---

# Giai đoạn B — Tài khoản cư dân (19–20/08)

## Task 7: Cột `account_status` và chốt chặn đăng nhập

**Files:**
- Modify: `src/models/db.py`, `src/models/schemas.py`, `src/api/deps.py`
- Create: `alembic/versions/<rev>_add_account_status.py`
- Test: `tests/test_api/test_auth.py`

**Interfaces:**
- Produces: `AccountStatus = Literal["active", "locked"]`; `User.account_status`; mọi request của tài khoản `locked` trả 403 với `detail = "Tài khoản đã bị Ban quản lý tạm khoá"`. Task 8 và Task 9 dùng.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `tests/test_api/test_auth.py`:

```python
@pytest.mark.asyncio
async def test_tai_khoan_bi_khoa_khong_goi_duoc_api(client, db_session):
    from src.models.db import User

    user = db_session.get(User, 2)
    user.account_status = "locked"
    db_session.commit()

    r = await client.get("/api/v1/profile", headers={"X-User-Id": "2"})
    assert r.status_code == 403
    assert "tạm khoá" in r.json()["detail"]


@pytest.mark.asyncio
async def test_tai_khoan_binh_thuong_van_goi_duoc(client):
    r = await client.get("/api/v1/profile", headers={"X-User-Id": "2"})
    assert r.status_code == 200
```

- [ ] **Step 2: Chạy test cho chắc là hỏng**

Run: `pytest tests/test_api/test_auth.py -k bi_khoa -v`
Expected: FAIL — `AttributeError` vì `User` chưa có `account_status`.

- [ ] **Step 3: Thêm kiểu vào schemas**

Trong `src/models/schemas.py`, cạnh `OwnershipType`:

```python
# Khoá tài khoản chặn ở BACKEND, không đụng Supabase Auth: người bị khoá vẫn
# đăng nhập được và vẫn có JWT hợp lệ, nhưng mọi lời gọi API trả 403.
AccountStatus = Literal["active", "locked"]
```

- [ ] **Step 4: Thêm cột vào model**

Trong `src/models/db.py`, khai hằng cạnh `ROLES`:

```python
ACCOUNT_STATUSES = ("active", "locked")
```

và trong `class User`, sau `role`:

```python
    # Khoá do BQL đặt. Kiểm trong `get_current_user` nên áp cho MỌI endpoint,
    # không phải nhớ gắn từng chỗ.
    account_status: Mapped[str] = mapped_column(
        SAEnum(*ACCOUNT_STATUSES, name="account_status", native_enum=False),
        default="active",
        server_default="active",
        nullable=False,
    )
```

- [ ] **Step 5: Chặn trong `get_current_user`**

Trong `src/api/deps.py`, thêm sau `_UNAUTHORIZED`:

```python
_LOCKED = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Tài khoản đã bị Ban quản lý tạm khoá",
)


def _ensure_active(user: dict[str, Any]) -> dict[str, Any]:
    """Chặn tài khoản bị khoá, áp cho CẢ HAI nhánh xác thực.

    Chỉ chặn nhánh JWT thì trên môi trường dev tài khoản bị khoá vẫn dùng được
    — mà bản demo chạy đúng nhánh `X-User-Id` đó.
    """
    if user.get("account_status") == "locked":
        raise _LOCKED
    return user
```

rồi trong `get_current_user` đổi cả hai chỗ `return user` thành `return _ensure_active(user)`.

- [ ] **Step 6: Lộ trường ra `_user_dict`**

Trong `src/services/store.py`, thêm vào dict trả về của `_user_dict`:

```python
        "account_status": user.account_status,
```

- [ ] **Step 7: Chạy test cho chắc là xanh**

Run: `pytest tests/test_api/test_auth.py -v`
Expected: PASS.

- [ ] **Step 8: Viết migration**

Run: `python -m alembic revision -m "add account status"`

Sửa file vừa sinh — **không dùng autogenerate**, nó sẽ sinh thẳng `nullable=False` và vỡ trên bảng đã có 41 dòng:

```python
revision: str = "<rev vừa sinh>"
down_revision: Union[str, Sequence[str], None] = "4b4ea98a4e85"


def upgrade() -> None:
    # Ba bước, không gộp: thêm nullable → backfill → mới khoá NOT NULL.
    op.add_column("users", sa.Column("account_status", sa.String(length=20)))
    op.execute("UPDATE users SET account_status = 'active'")
    op.alter_column(
        "users",
        "account_status",
        nullable=False,
        server_default="active",
        existing_type=sa.String(length=20),
    )


def downgrade() -> None:
    op.drop_column("users", "account_status")
```

- [ ] **Step 9: Thử migration cả hai chiều**

```bash
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic upgrade head
```

Chạy trên DB phát triển cục bộ. **Không chạy lên `DATABASE_URL` trong `.env`** — nó trỏ vào Supabase production thật.

- [ ] **Step 10: Commit**

```bash
ruff check src/ tests/ && pytest -q
git add src/models/db.py src/models/schemas.py src/api/deps.py src/services/store.py alembic/versions/ tests/test_api/test_auth.py
git commit -m "feat: khoá tài khoản cư dân, chặn ở tầng xác thực"
```

---

## Task 8: Endpoint khoá/mở và đặt lại mật khẩu

**Files:**
- Modify: `src/services/supabase_admin.py`, `src/services/store.py`, `src/models/schemas.py`, `src/api/routes.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_api/test_routes.py`

**Interfaces:**
- Consumes: `AccountStatus` từ Task 7; `_build_checklist(db, user)` đã có sẵn trong `routes.py`.
- Produces: `PATCH /api/v1/admin/residents/{user_id}/status` và `POST /api/v1/admin/residents/{user_id}/reset-password`; `supabase_admin.update_auth_password(auth_user_id: uuid.UUID, password: str) -> None`; `store.set_account_status(db, user_id, status) -> dict`. **Ba thứ Task 9 dùng lại:** schema `ResidentDetailResponse`, helper `_require_resident_record(db, user_id) -> dict`, helper `_build_resident_detail(db, user_id) -> ResidentDetailResponse`.

- [ ] **Step 1: Đổi `fake_auth_provisioning` thành `autouse` TRƯỚC khi viết gì khác**

Làm trước có chủ đích: nếu viết test đặt-lại-mật-khẩu trước, một lần chạy lỡ sẽ **đổi mật khẩu của tài khoản có thật trên production** và người đó mất quyền đăng nhập. Không dọn lại được.

Trong `tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def fake_auth_provisioning(monkeypatch):
    """Chặn mọi lời gọi Supabase Admin API trong test.

    `autouse` từ 18/08. Trước đó là fixture tự chọn vì chỉ một test tạo tài
    khoản. Nay còn có đặt lại mật khẩu, và hậu quả của việc quên nặng hơn hẳn:
    không phải đẻ ra một user thừa rồi đi xoá tay (11/08), mà là đổi mật khẩu
    của một tài khoản có thật — người đó mất quyền đăng nhập, không hoàn tác
    được. Cùng lý do `fake_storage` là autouse.
    """
    from src.api import routes

    monkeypatch.setattr(
        routes, "create_auth_user", lambda _email, _password: uuid.uuid4()
    )
    monkeypatch.setattr(routes, "update_auth_password", lambda _uid, _password: None)
```

Bước này chưa chạy được cho tới Step 4 (chưa có `update_auth_password` để patch) — đó là dự tính, không phải lỗi.

- [ ] **Step 2: Viết test thất bại**

```python
# --- Quản lý tài khoản cư dân (18/08) -----------------------------------


@pytest.mark.asyncio
async def test_bql_khoa_va_mo_tai_khoan(client):
    locked = await client.patch(
        "/api/v1/admin/residents/2/status",
        json={"account_status": "locked"},
        headers=ADMIN,
    )
    assert locked.status_code == 200
    assert locked.json()["account_status"] == "locked"

    assert (await client.get("/api/v1/profile", headers=OWNER)).status_code == 403

    await client.patch(
        "/api/v1/admin/residents/2/status",
        json={"account_status": "active"},
        headers=ADMIN,
    )
    assert (await client.get("/api/v1/profile", headers=OWNER)).status_code == 200


@pytest.mark.asyncio
async def test_khong_khoa_duoc_tai_khoan_bql(client):
    """User 1 là BQL. Quy tắc 'chỉ cư dân' gánh luôn việc BQL không tự khoá mình."""
    r = await client.patch(
        "/api/v1/admin/residents/1/status",
        json={"account_status": "locked"},
        headers=ADMIN,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cu_dan_khong_khoa_duoc_ai(client):
    r = await client.patch(
        "/api/v1/admin/residents/3/status",
        json={"account_status": "locked"},
        headers=OWNER,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_dat_lai_mat_khau_tra_mat_khau_tam(client):
    """User 2 đã gắn auth_user_id trong conftest."""
    r = await client.post("/api/v1/admin/residents/2/reset-password", headers=ADMIN)
    assert r.status_code == 200
    assert len(r.json()["temporary_password"]) >= 12


@pytest.mark.asyncio
async def test_dat_lai_mat_khau_khi_chua_co_tai_khoan_dang_nhap_tra_409(client):
    """User 3 chưa có auth_user_id — không có mật khẩu nào để đặt lại.

    Không phải trường hợp lý thuyết: `seed_data` xoá sạch auth_user_id, ai chạy
    seed mà quên `provision_auth` là rơi vào đúng đây.
    """
    r = await client.post("/api/v1/admin/residents/3/reset-password", headers=ADMIN)
    assert r.status_code == 409
```

- [ ] **Step 3: Chạy test cho chắc là hỏng**

Run: `pytest tests/test_api/test_routes.py -k "khoa or dat_lai" -v`
Expected: FAIL — 404, route chưa tồn tại.

- [ ] **Step 4: Thêm `update_auth_password`**

Trong `src/services/supabase_admin.py`:

```python
def update_auth_password(auth_user_id: uuid.UUID, password: str) -> None:
    """Đặt lại mật khẩu cho một tài khoản đã có. Dùng khi cư dân quên mật khẩu.

    Không gửi thư đặt lại: tài khoản demo dùng tên miền @moveinmate.demo không
    tồn tại nên thư không bao giờ tới. BQL đọc mật khẩu tạm cho cư dân, đúng
    nguyên tắc "BQL cấp tài khoản, cư dân không tự đăng ký".
    """
    base, headers = _config()
    try:
        response = httpx.put(
            f"{base}/admin/users/{auth_user_id}",
            headers=headers,
            json={"password": password},
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise SupabaseAdminError(f"Không gọi được Supabase: {exc}") from exc

    if response.status_code >= 400:
        detail = response.json().get("msg") or response.text
        raise SupabaseAdminError(f"Supabase từ chối đổi mật khẩu: {detail}")
```

- [ ] **Step 5: Thêm hàm store**

Trong `src/services/store.py`:

```python
def set_account_status(db: Session, user_id: int, account_status: str) -> dict[str, Any]:
    user = db.get(User, user_id)
    user.account_status = account_status
    db.commit()
    return _user_dict(user)
```

- [ ] **Step 6: Thêm schema**

Trong `src/models/schemas.py`:

```python
class AccountStatusUpdateRequest(BaseModel):
    account_status: AccountStatus


class ResidentDetailResponse(BaseModel):
    """Toàn cảnh một cư dân, cho trang BQL.

    Ghép ba schema đã có thay vì bịa một schema phẳng mới: giao diện đã có sẵn
    component render checklist và hồ sơ ở khu cư dân, nên trang BQL dùng lại
    được, không phải viết lại logic hiển thị.

    Dùng `ApplicationResponse` chứ không phải `AdminApplicationResponse` — đã
    biết đang xem ai thì user_id/full_name/apartment là thừa.
    """

    profile: ProfileResponse
    checklist: ChecklistResponse
    applications: list[ApplicationResponse]
    account_status: AccountStatus


class TemporaryPasswordResponse(BaseModel):
    """Mật khẩu tạm sau khi đặt lại.

    Chỉ xuất hiện đúng một lần ở phản hồi này; hệ thống không lưu và không có
    cách xem lại. Quên nữa thì đặt lại tiếp.
    """

    temporary_password: str
```

- [ ] **Step 7: Thêm helper dùng chung và hai route**

Trong `src/api/routes.py`:

```python
def _require_resident_record(db: Session, user_id: int) -> dict[str, Any]:
    """Hồ sơ cư dân, hoặc 404.

    Chặn luôn cả `role == "admin"`: mở thao tác quản trị lên một tài khoản BQL
    sẽ cho phép BQL tự khoá mình ra khỏi hệ thống, và hiện một checklist nhận
    nhà vô nghĩa — đúng lỗi mà `require_resident` sinh ra để chặn.
    """
    resident = store.get_user(db, user_id)
    if resident is None or resident["role"] != "resident":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cư dân này."
        )
    return resident


def _build_resident_detail(db: Session, user_id: int) -> ResidentDetailResponse:
    """Toàn cảnh một cư dân. Task 9 dùng lại nguyên hàm này cho `GET`."""
    resident = _require_resident_record(db, user_id)
    return ResidentDetailResponse(
        profile=ProfileResponse(**resident),
        checklist=_build_checklist(db, resident),
        applications=store.list_applications(db, user_id),
        account_status=resident["account_status"],
    )


@router.patch(
    "/admin/residents/{user_id}/status", response_model=ResidentDetailResponse
)
async def set_resident_account_status(
    user_id: int,
    payload: AccountStatusUpdateRequest,
    _admin: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ResidentDetailResponse:
    """Khoá hoặc mở tài khoản cư dân.

    Trả về TOÀN BỘ chi tiết chứ không riêng trường vừa đổi, theo nếp của
    `PATCH /checklist/{item_id}`: giao diện cập nhật cả trang trong một lượt.
    """
    _require_resident_record(db, user_id)
    store.set_account_status(db, user_id, payload.account_status)
    return _build_resident_detail(db, user_id)


@router.post(
    "/admin/residents/{user_id}/reset-password",
    response_model=TemporaryPasswordResponse,
)
async def reset_resident_password(
    user_id: int,
    _admin: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TemporaryPasswordResponse:
    resident = _require_resident_record(db, user_id)
    if resident["auth_user_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cư dân này chưa được cấp tài khoản đăng nhập.",
        )

    password = generate_password()
    try:
        update_auth_password(resident["auth_user_id"], password)
    except SupabaseAdminError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không đặt lại được mật khẩu: {exc}",
        ) from exc
    return TemporaryPasswordResponse(temporary_password=password)
```

`ProfileResponse(**resident)` bỏ qua các khoá thừa nhờ cấu hình mặc định của Pydantic v2 — nếu model bật `extra="forbid"` thì lọc trước bằng `ProfileResponse.model_fields`.

`_user_dict` chưa trả `auth_user_id`; thêm vào (`"auth_user_id": user.auth_user_id`) và **kiểm rằng `ProfileResponse` không có trường đó** nên nó không lọt ra API.

Import thêm: `update_auth_password`, `generate_password`, `SupabaseAdminError` từ `src.services.supabase_admin`.

- [ ] **Step 8: Chạy test cho chắc là xanh**

Run: `pytest tests/test_api/ -v -k "khoa or dat_lai"`
Expected: PASS, 5 test.

- [ ] **Step 9: Commit**

```bash
ruff check src/ tests/ && pytest -q
git add src/services/supabase_admin.py src/services/store.py src/models/schemas.py src/api/routes.py tests/
git commit -m "feat: BQL khoá/mở tài khoản và đặt lại mật khẩu cư dân"
```

---

# Giai đoạn C — Chi tiết cư dân (20–21/08)

## Task 9: Endpoint chi tiết cư dân

**Files:**
- Modify: `src/models/schemas.py`, `src/api/routes.py`
- Test: `tests/test_api/test_routes.py`

**Interfaces:**
- Consumes: `ResidentDetailResponse`, `_require_resident_record`, `_build_resident_detail` — cả ba đã viết ở Task 8.
- Produces: `GET /api/v1/admin/residents/{user_id}` → `ResidentDetailResponse`; `ResidentProgress.account_status`.

Task này mỏng có chủ đích: Task 8 đã dựng sẵn toàn bộ phần dựng dữ liệu, ở đây chỉ mở nó ra thành một endpoint đọc và bổ sung trường vào dashboard.

- [ ] **Step 1: Viết test thất bại**

```python
@pytest.mark.asyncio
async def test_bql_xem_duoc_chi_tiet_mot_cu_dan(client):
    await _create(client, CAR_CARD_ITEM)

    r = await client.get("/api/v1/admin/residents/2", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["full_name"] == "Trần Văn An"
    assert body["account_status"] == "active"
    assert len(body["checklist"]["items"]) > 0
    assert len(body["applications"]) == 1


@pytest.mark.asyncio
async def test_chi_tiet_phan_anh_muc_da_hoan_thanh(client):
    """conftest đánh dấu user 2 đã xong mục 1."""
    body = (await client.get("/api/v1/admin/residents/2", headers=ADMIN)).json()
    done = [i["id"] for i in body["checklist"]["items"] if i["completed"]]
    assert 1 in done


@pytest.mark.asyncio
async def test_cu_dan_khong_xem_duoc_chi_tiet_nguoi_khac(client):
    r = await client.get("/api/v1/admin/residents/3", headers=OWNER)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_chi_tiet_tai_khoan_bql_tra_404(client):
    r = await client.get("/api/v1/admin/residents/1", headers=ADMIN)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_chi_tiet_cu_dan_khong_ton_tai_tra_404(client):
    r = await client.get("/api/v1/admin/residents/9999", headers=ADMIN)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_bql_co_trang_thai_tai_khoan(client):
    rows = (await client.get("/api/v1/admin/dashboard", headers=ADMIN)).json()
    assert all("account_status" in r for r in rows["residents"])
```

- [ ] **Step 2: Chạy test cho chắc là hỏng**

Run: `pytest tests/test_api/test_routes.py -k "chi_tiet or trang_thai_tai_khoan" -v`
Expected: FAIL.

- [ ] **Step 3: Thêm trường vào schema dashboard**

Trong `src/models/schemas.py`, thêm vào `ResidentProgress`:

```python
    account_status: AccountStatus
```

- [ ] **Step 4: Thêm route**

Trong `src/api/routes.py`, dưới hai route của Task 8:

```python
@router.get("/admin/residents/{user_id}", response_model=ResidentDetailResponse)
async def resident_detail(
    user_id: int,
    _admin: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ResidentDetailResponse:
    """Toàn cảnh một cư dân — chỗ nối hai bảng phẳng của khu BQL lại với nhau.

    Không thêm endpoint danh sách: `GET /admin/dashboard` đã trả toàn bộ cư dân
    kèm tiến độ. 41 cư dân thì lọc và tìm kiếm làm ở client.
    """
    return _build_resident_detail(db, user_id)
```

Trong endpoint `dashboard`, thêm vào dict mỗi dòng:

```python
                "account_status": resident["account_status"],
```

- [ ] **Step 5: Chạy test cho chắc là xanh**

Run: `pytest tests/test_api/ -v`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit**

```bash
ruff check src/ tests/ && pytest -q
git add src/models/schemas.py src/api/routes.py tests/test_api/test_routes.py
git commit -m "feat: một trang cho biết toàn cảnh một cư dân"
```

---

# Giai đoạn D — Hạ tầng Chroma (20–21/08)

## Task 10: Chốt ranh giới với Hải bằng văn bản

Việc **đầu tiên** của US-08, không phải việc làm sau. Charter mục 12.

**Files:**
- Modify: `docs/ROLES_AND_PLAN.md`

- [ ] **Step 1: Ghi phần phân chia vào `ROLES_AND_PLAN.md`**

```markdown
### US-08 — chia việc giữa vai AI và vai BE (chốt 18/08)

`ingest` thuộc vai AI. Phân chia:

| Ai | Việc |
|---|---|
| **Hải** | Cho `ingest_file` nhận tài liệu do BQL gửi; xác nhận nhịp batch và backoff vẫn đúng khi gọi từ tiến trình web thay vì từ script |
| **Hiếu** | Endpoint `POST /admin/documents`, cột `embed_status`, gắn Railway Volume, seed lúc khởi động, `/health/deep` |

Không ai đụng file của vai kia. `data/chroma/` vẫn chỉ vai AI chạy `ingest_kb`
thủ công; endpoint mới ghi vào cùng collection nhưng qua `ingest_file`.
```

- [ ] **Step 2: Commit và gửi Hải**

```bash
git add docs/ROLES_AND_PLAN.md
git commit -m "docs: chốt ranh giới vai cho US-08 trước khi code song song"
```

---

## Task 11: `/health/deep`

Bị kéo lại vào phạm vi vì Task 12/13: một khi Chroma nằm trên volume có thể rỗng, `collection.count()` là thứ **duy nhất** phân biệt "hệ thống khoẻ" với "hệ thống câm".

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_api/test_routes.py`

**Interfaces:**
- Produces: `GET /health/deep` → 200 `{"database": "ok", "chroma": {"status": "ok", "documents": <int>}}`, hoặc 503 khi một thành phần chết.

- [ ] **Step 1: Viết test thất bại**

```python
@pytest.mark.asyncio
async def test_health_deep_bao_so_chunk_trong_chroma(client, monkeypatch):
    from src.services import vectorstore

    class _FakeCollection:
        def count(self) -> int:
            return 42

    class _FakeStore:
        _collection = _FakeCollection()

    monkeypatch.setattr(vectorstore, "get_vectorstore", lambda: _FakeStore())

    r = await client.get("/health/deep")
    assert r.status_code == 200
    assert r.json()["chroma"]["documents"] == 42


@pytest.mark.asyncio
async def test_health_deep_tra_503_khi_chroma_rong(client, monkeypatch):
    """Chroma rỗng = trợ lý từ chối MỌI câu hỏi, mà không chỉ báo nào đỏ.
    Đúng kiểu sự cố 11/08."""
    from src.services import vectorstore

    class _EmptyCollection:
        def count(self) -> int:
            return 0

    class _FakeStore:
        _collection = _EmptyCollection()

    monkeypatch.setattr(vectorstore, "get_vectorstore", lambda: _FakeStore())

    r = await client.get("/health/deep")
    assert r.status_code == 503
```

- [ ] **Step 2: Chạy test cho chắc là hỏng**

Run: `pytest tests/test_api/test_routes.py -k health_deep -v`
Expected: FAIL — 404.

- [ ] **Step 3: Viết endpoint**

Trong `src/main.py`:

```python
@app.get("/health/deep")
async def health_deep(db: Session = Depends(get_db)) -> JSONResponse:
    """Kiểm thành phần thật, không chỉ kiểm tiến trình còn sống.

    Tiền lệ 11/08: index Chroma hỏng mà mọi chỉ báo vẫn xanh suốt nhiều giờ.
    Từ khi Chroma nằm trên volume có thể rỗng, `count() == 0` là chế độ hỏng
    NGHIÊM TRỌNG chứ không phải trạng thái hợp lệ: retrieve rỗng khiến guard
    chống bịa từ chối mọi câu hỏi, và không màn hình nào báo lỗi.
    """
    report: dict[str, Any] = {}
    healthy = True

    try:
        db.execute(text("SELECT 1"))
        report["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 — báo cáo mọi lỗi hạ tầng
        report["database"] = f"error: {type(exc).__name__}"
        healthy = False

    try:
        count = vectorstore.get_vectorstore()._collection.count()
        report["chroma"] = {"status": "ok" if count else "empty", "documents": count}
        healthy = healthy and count > 0
    except Exception as exc:  # noqa: BLE001
        report["chroma"] = {"status": f"error: {type(exc).__name__}"}
        healthy = False

    return JSONResponse(report, status_code=200 if healthy else 503)
```

- [ ] **Step 4: Chạy test cho chắc là xanh**

Run: `pytest tests/test_api/test_routes.py -k health_deep -v`
Expected: PASS, 2 test.

- [ ] **Step 5: Commit**

```bash
ruff check src/ tests/ && pytest -q
git add src/main.py tests/test_api/test_routes.py
git commit -m "feat: /health/deep phân biệt hệ thống khoẻ với hệ thống câm"
```

---

## Task 12: Seed Chroma lúc khởi động

**Files:**
- Create: `src/services/chroma_seed.py`
- Modify: `src/main.py`, `Dockerfile`
- Test: `tests/test_services/test_chroma_seed.py`

**Interfaces:**
- Produces: `ensure_seeded(persist_dir: str, seed_dir: str) -> bool` — trả `True` nếu đã chép.

- [ ] **Step 1: Viết test thất bại**

`tests/test_services/test_chroma_seed.py`:

```python
from pathlib import Path

from src.services.chroma_seed import ensure_seeded


def test_chep_khi_thu_muc_dich_rong(tmp_path: Path):
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "chroma.sqlite3").write_bytes(b"giả")
    target = tmp_path / "chroma"

    assert ensure_seeded(str(target), str(seed)) is True
    assert (target / "chroma.sqlite3").read_bytes() == b"giả"


def test_khong_de_len_du_lieu_da_co(tmp_path: Path):
    """Chép đè lên volume đang có dữ liệu sẽ XOÁ tài liệu BQL vừa nạp."""
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "chroma.sqlite3").write_bytes(b"giống")
    target = tmp_path / "chroma"
    target.mkdir()
    (target / "chroma.sqlite3").write_bytes(b"thật")

    assert ensure_seeded(str(target), str(seed)) is False
    assert (target / "chroma.sqlite3").read_bytes() == b"thật"


def test_khong_co_seed_thi_khong_no(tmp_path: Path):
    assert ensure_seeded(str(tmp_path / "chroma"), str(tmp_path / "khong-ton-tai")) is False
```

- [ ] **Step 2: Chạy test cho chắc là hỏng**

Run: `pytest tests/test_services/test_chroma_seed.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Viết module**

`src/services/chroma_seed.py`:

```python
"""Nạp mồi Chroma vào volume rỗng lúc khởi động.

Vì sao cần: từ 18/08 `data/chroma` là một Railway Volume để tài liệu BQL nạp
không mất sau mỗi lần deploy. Volume mới gắn thì RỖNG. Container khởi động với
Chroma rỗng → `rag_retrieve` không trả về gì → guard chống bịa kích hoạt ở mọi
câu hỏi → trợ lý từ chối trả lời toàn bộ, mà không màn hình nào báo lỗi và mọi
chỉ báo vẫn xanh.

Bản mồi KHÔNG thể nằm ở chính đường dẫn volume: mount che khuất nội dung image
ở đấy. Dockerfile chép sang `/app/data/chroma_seed`, module này chép ngược lại.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_seeded(persist_dir: str, seed_dir: str) -> bool:
    """Chép bản mồi vào `persist_dir` nếu nó rỗng. Trả True nếu đã chép."""
    target = Path(persist_dir)
    seed = Path(seed_dir)

    if not seed.is_dir():
        logger.warning("Không có bản mồi Chroma tại %s", seed)
        return False

    if target.is_dir() and any(target.iterdir()):
        # KHÔNG chép đè: sẽ xoá mất tài liệu BQL vừa nạp trên production.
        return False

    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(seed, target, dirs_exist_ok=True)
    logger.info("Đã nạp mồi Chroma từ %s", seed)
    return True
```

- [ ] **Step 4: Chạy test cho chắc là xanh**

Run: `pytest tests/test_services/test_chroma_seed.py -v`
Expected: PASS, 3 test.

- [ ] **Step 5: Gọi lúc khởi động**

`src/main.py:11` đã có `@asynccontextmanager async def lifespan(app)`. Thêm vào **trước** dòng `yield` trong đó — tức trước khi phục vụ request đầu tiên:

```python
    ensure_seeded(get_settings().chroma_persist_dir, "./data/chroma_seed")
```

Đặt sau `yield` là seed chạy lúc tắt máy, vô dụng.

- [ ] **Step 6: Chép bản mồi vào image**

Trong `Dockerfile`, sau bước `COPY` mã nguồn:

```dockerfile
# Bản mồi Chroma. KHÔNG để ở /app/data/chroma — volume mount sẽ che khuất nó.
RUN cp -r /app/data/chroma /app/data/chroma_seed
```

- [ ] **Step 7: Commit**

```bash
ruff check src/ tests/ && pytest -q
git add src/services/chroma_seed.py src/main.py Dockerfile tests/test_services/test_chroma_seed.py
git commit -m "feat: nạp mồi Chroma khi volume còn rỗng"
```

---

## Task 13: Gắn Railway Volume

Task thao tác hạ tầng, không có test tự động. Làm **sớm**, đây là thay đổi rủi ro nhất trong kế hoạch.

**Files:** không sửa file nào — cấu hình trên Railway.

- [ ] **Step 1: Ghi lại `collection.count()` hiện tại**

```bash
curl -s https://<host>/health/deep
```

Ghi con số lại. Đây là mốc để so sau khi gắn volume.

- [ ] **Step 2: Gắn volume (PowerShell, không phải Git Bash)**

Trên Railway dashboard: service backend → Variables/Settings → thêm Volume, mount path `/app/data/chroma`.

- [ ] **Step 3: Deploy lại và xem log khởi động**

```powershell
railway up
railway logs
```

Trong log phải thấy dòng `Đã nạp mồi Chroma từ ./data/chroma_seed`.

- [ ] **Step 4: Nghiệm thu bằng nội dung, không bằng header**

```bash
curl -s https://<host>/health/deep
```

`chroma.documents` phải **bằng con số ở Step 1**. Nếu là `0` → 503 → volume rỗng và seed không chạy: kiểm lại bước `cp` trong Dockerfile trước khi làm gì khác.

Rồi hỏi trợ lý một câu có trong KB và xác nhận vẫn có `sources[]`. **Không** dùng header `Age` làm bằng chứng deploy — đã hai lần kết luận sai vì nó.

- [ ] **Step 5: Ghi vào DEPLOY.md**

Sửa `docs/DEPLOY.md:211`, đổi mục "hướng xử lý" thành đã làm, kèm ngày và cảnh báo bản mồi không được nằm ở chính đường dẫn mount.

```bash
git add docs/DEPLOY.md
git commit -m "docs: Chroma đã chuyển sang Railway Volume"
```

---

# Giai đoạn E — BQL nạp tài liệu (22–23/08)

## Task 14: Cột `embed_status`

**Files:**
- Modify: `src/models/db.py`, `src/models/schemas.py`
- Create: `alembic/versions/<rev>_add_embed_status.py`

**Interfaces:**
- Produces: `Document.embed_status`; `EmbedStatus = Literal["pending", "processing", "ready", "failed"]`.

- [ ] **Step 1: Thêm kiểu**

Trong `src/models/schemas.py`:

```python
EmbedStatus = Literal["pending", "processing", "ready", "failed"]
```

- [ ] **Step 2: Thêm cột**

Trong `src/models/db.py`, hằng cạnh `ACCOUNT_STATUSES`:

```python
EMBED_STATUSES = ("pending", "processing", "ready", "failed")
```

và trong `class Document`:

```python
    # Embed mất từ nửa phút tới vài phút (15 chunk mỗi lượt, nghỉ 12 giây) nên
    # chạy nền. Container chết giữa chừng thì bản ghi kẹt ở `processing` và BQL
    # bấm nạp lại — đủ cho phạm vi này, không dựng hàng đợi.
    embed_status: Mapped[str] = mapped_column(
        SAEnum(*EMBED_STATUSES, name="embed_status", native_enum=False),
        default="ready",
        server_default="ready",
        nullable=False,
    )
```

Mặc định `ready` chứ không phải `pending`: mọi dòng đang có đều đã được ingest xong từ trước.

- [ ] **Step 3: Migration**

Run: `python -m alembic revision -m "add embed status"`

```python
down_revision: Union[str, Sequence[str], None] = "<rev của Task 7>"


def upgrade() -> None:
    op.add_column("documents", sa.Column("embed_status", sa.String(length=20)))
    op.execute("UPDATE documents SET embed_status = 'ready'")
    op.alter_column(
        "documents",
        "embed_status",
        nullable=False,
        server_default="ready",
        existing_type=sa.String(length=20),
    )


def downgrade() -> None:
    op.drop_column("documents", "embed_status")
```

- [ ] **Step 4: Thử cả hai chiều**

```bash
python -m alembic upgrade head && python -m alembic downgrade -1 && python -m alembic upgrade head
```

- [ ] **Step 5: Commit**

```bash
ruff check src/ tests/ && pytest -q
git add src/models/db.py src/models/schemas.py alembic/versions/
git commit -m "feat: theo dõi trạng thái embed của từng tài liệu"
```

---

## Task 15: Endpoint nạp tài liệu

**Files:**
- Modify: `src/models/schemas.py`, `src/services/store.py`, `src/api/routes.py`
- Test: `tests/test_api/test_routes.py`

**Interfaces:**
- Consumes: `EmbedStatus` (Task 14); `ingest.ingest_file(db, path)` — bản Hải sửa ở Task 10.
- Produces: `POST /api/v1/admin/documents`, `GET /api/v1/admin/documents`.

- [ ] **Step 1: Viết test thất bại**

```python
# --- BQL nạp tài liệu (US-08) -------------------------------------------


@pytest.fixture
def fake_ingest(monkeypatch):
    """Chặn embed thật: nó gọi Google API và tiêu hạn mức dùng chung cả nhóm."""
    from src.api import routes

    called: list[str] = []
    monkeypatch.setattr(routes, "ingest_file", lambda _db, path: called.append(str(path)) or 3)
    return called


@pytest.mark.asyncio
async def test_bql_nap_tai_lieu_moi(client, fake_ingest):
    r = await client.post(
        "/api/v1/admin/documents",
        json={"title": "Quy trình mới", "content": "# Quy trình\n\nNội dung."},
        headers=ADMIN,
    )
    assert r.status_code == 201
    assert r.json()["title"] == "Quy trình mới"
    assert r.json()["embed_status"] in ("pending", "processing", "ready")


@pytest.mark.asyncio
async def test_cu_dan_khong_nap_duoc_tai_lieu(client, fake_ingest):
    r = await client.post(
        "/api/v1/admin/documents",
        json={"title": "X", "content": "Y"},
        headers=OWNER,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_tai_lieu_rong_bi_tu_choi(client, fake_ingest):
    r = await client.post(
        "/api/v1/admin/documents",
        json={"title": "X", "content": "   "},
        headers=ADMIN,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_bql_xem_duoc_danh_sach_tai_lieu(client, fake_ingest):
    await client.post(
        "/api/v1/admin/documents",
        json={"title": "Quy trình mới", "content": "# A\n\nB."},
        headers=ADMIN,
    )
    rows = (await client.get("/api/v1/admin/documents", headers=ADMIN)).json()
    assert any(d["title"] == "Quy trình mới" for d in rows)
```

- [ ] **Step 2: Chạy test cho chắc là hỏng**

Run: `pytest tests/test_api/test_routes.py -k tai_lieu -v`
Expected: FAIL.

- [ ] **Step 3: Thêm schema**

```python
class DocumentIngestRequest(BaseModel):
    """BQL dán nội dung quy trình mới.

    Dán chữ chứ không tải tệp: `ingest_file` đòi `.md` có frontmatter YAML hợp
    lệ mà BQL không gõ YAML, và đọc PDF nằm ngoài phạm vi. Backend tự sinh
    frontmatter với `source_type: bql_internal`.
    """

    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)

    @field_validator("content")
    @classmethod
    def khong_duoc_toan_khoang_trang(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nội dung tài liệu không được để trống")
        return v


class DocumentResponse(BaseModel):
    document_id: int
    title: str
    file_path: str
    embed_status: EmbedStatus
    uploaded_at: datetime
```

Khớp đúng các cột của `Document` trong `src/models/db.py:293-304` (`document_id`, `title`, `file_path`, `uploaded_by`, `uploaded_at`) cộng cột mới ở Task 14. **Không có `chunk_count`** — số chunk nằm ở Chroma, không ở bảng này.

- [ ] **Step 4: Viết route**

```python
@router.post(
    "/admin/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_document(
    payload: DocumentIngestRequest,
    background: BackgroundTasks,
    _admin: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """US-08 — BQL tự cập nhật tri thức của trợ lý.

    Embed chạy NỀN: 15 chunk mỗi lượt gọi, nghỉ 12 giây giữa các lượt, nên một
    tài liệu dài mất vài phút. Giữ trong request sẽ timeout.
    """
    slug = slugify(payload.title)
    path = KB_DIR / "bql" / f"{slug}.md"
    path.write_text(
        f"---\ntitle: {payload.title}\nsource_type: bql_internal\n---\n\n{payload.content}",
        encoding="utf-8",
    )

    record = store.create_document_record(db, str(path), payload.title, "pending")
    background.add_task(_embed_document, record["document_id"], path)
    return record
```

Hàm nền:

```python
def _embed_document(document_id: int, path: Path) -> None:
    """Chạy ngoài request. Tự mở session riêng — session của request đã đóng."""
    with SessionLocal() as db:
        store.set_embed_status(db, document_id, "processing")
        try:
            ingest_file(db, path)
        except Exception:  # noqa: BLE001 — mọi lỗi đều phải hiện lên giao diện
            logger.exception("Embed tài liệu %s thất bại", document_id)
            store.set_embed_status(db, document_id, "failed")
        else:
            store.set_embed_status(db, document_id, "ready")
```

`GET /admin/documents` trả `store.list_documents(db)`.

`slugify` — nếu repo chưa có, viết hàm nhỏ trong `src/services/ingest.py` bỏ dấu tiếng Việt và thay khoảng trắng bằng `-`. **Đây là file của vai AI**: nhờ Hải thêm, hoặc chốt trong Task 10 rằng phần này thuộc Hiếu.

- [ ] **Step 5: Thêm hàm store**

```python
def create_document_record(
    db: Session, file_path: str, title: str, embed_status: str
) -> dict[str, Any]:
    doc = Document(file_path=file_path, title=title, embed_status=embed_status)
    db.add(doc)
    db.commit()
    return _document_dict(doc)


def set_embed_status(db: Session, document_id: int, embed_status: str) -> None:
    doc = db.get(Document, document_id)
    if doc is not None:
        doc.embed_status = embed_status
        db.commit()


def list_documents(db: Session) -> list[dict[str, Any]]:
    return [
        _document_dict(d)
        for d in db.scalars(select(Document).order_by(Document.document_id.desc()))
    ]
```

và helper dựng dict, cạnh `_user_dict`:

```python
def _document_dict(doc: Document) -> dict[str, Any]:
    return {
        "document_id": doc.document_id,
        "title": doc.title,
        "file_path": doc.file_path,
        "embed_status": doc.embed_status,
        "uploaded_at": _as_utc(doc.uploaded_at),
    }
```

Import cần thêm ở `src/api/routes.py`: `BackgroundTasks` từ `fastapi`, `Path` từ `pathlib`, `SessionLocal` từ `src.database`, `ingest_file` và `KB_DIR` từ `src.services.ingest`, cùng một `logger = logging.getLogger(__name__)` nếu file chưa có.

- [ ] **Step 6: Chạy test cho chắc là xanh**

Run: `pytest tests/test_api/test_routes.py -k tai_lieu -v`
Expected: PASS, 4 test.

- [ ] **Step 7: Commit**

```bash
ruff check src/ tests/ && pytest -q
git status   # KHÔNG được có thay đổi trong data/chroma/
git commit -am "feat: BQL tự nạp tài liệu vào tri thức trợ lý"
```

⚠️ Nếu `git status` hiện `data/chroma/` bẩn: test đã chạm Chroma thật. Kiểm lại fixture `fake_ingest`, rồi `git checkout -- data/chroma/` và **kiểm `collection.count()`** sau đó.

---

# Giai đoạn F — Lớp phản hồi (22–23/08)

## Task 16: Toast

**Files:**
- Create: `web/app/components/Toast.tsx`
- Modify: `web/app/layout.tsx`

**Interfaces:**
- Produces: `<ToastProvider>` và `useToast()` trả `{ show(message: string, tone?: "success" | "error"): void }`.

- [ ] **Step 1: Viết component**

`web/app/components/Toast.tsx`:

```tsx
"use client";

import { createContext, useCallback, useContext, useState } from "react";

/**
 * Thông báo sau thao tác. Tự viết thay vì thêm thư viện: cần đúng một hình
 * dạng, và nó phải dùng bảng token màu sẵn có — thư viện ngoài mang giao diện
 * riêng rồi phải đi ghi đè. Thêm phụ thuộc vào bundle PWA sát demo cũng không
 * đáng.
 */
type Tone = "success" | "error";
type Toast = { id: number; message: string; tone: Tone };

const ToastContext = createContext<{ show: (m: string, t?: Tone) => void } | null>(
  null,
);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast phải nằm trong <ToastProvider>");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const show = useCallback((message: string, tone: Tone = "success") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-4 bottom-28 z-[60] flex flex-col items-center gap-2 lg:inset-x-auto lg:bottom-6 lg:right-6 lg:items-end"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={`pointer-events-auto max-w-sm rounded-lg px-4 py-3 text-sm shadow-lg ${
              t.tone === "error"
                ? "bg-red-600 text-white"
                : "bg-ink text-white"
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
```

`bottom-28` trên mobile để không bị thanh tab che.

- [ ] **Step 2: Bọc ứng dụng**

Trong `web/app/layout.tsx`, bọc `{children}` bằng `<ToastProvider>`.

- [ ] **Step 3: Gắn vào các thao tác đang im lặng**

Danh sách đóng, không rà soát thêm: tick mục checklist · nộp hồ sơ · tải ảnh minh chứng · BQL đổi trạng thái hồ sơ · BQL gán loại giấy tờ · khoá/mở tài khoản · đặt lại mật khẩu · nạp tài liệu.

Ở mỗi chỗ, sau khi lời gọi API thành công: `toast.show("Đã lưu thay đổi")`; trong `catch`: `toast.show("<việc gì> không thành công", "error")`.

- [ ] **Step 4: Kiểm bằng mắt**

Run: `cd web && npx tsc --noEmit && npm run dev`

Tick một mục checklist ở 390px → toast hiện phía trên thanh tab, không bị che, tự biến mất sau 4 giây.

- [ ] **Step 5: Commit**

```bash
git add web/app/components/Toast.tsx web/app/layout.tsx web/app/checklist/page.tsx
git commit -m "feat(web): thao tác nào cũng nói cho người dùng biết kết quả"
```

---

## Task 17: `EmptyState`, `ErrorState`, và không lộ thông điệp nội bộ

**Files:**
- Create: `web/app/components/EmptyState.tsx`, `web/app/components/ErrorState.tsx`
- Modify: `web/app/checklist/page.tsx:66`

- [ ] **Step 1: Hai component**

`EmptyState.tsx`:

```tsx
import type { LucideIcon } from "lucide-react";

export default function EmptyState({
  icon: Icon,
  title,
  hint,
}: {
  icon?: LucideIcon;
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border px-6 py-12 text-center">
      {Icon && <Icon className="h-8 w-8 text-muted" strokeWidth={1.5} />}
      <p className="text-sm font-medium text-ink">{title}</p>
      {hint && <p className="max-w-sm text-sm text-muted">{hint}</p>}
    </div>
  );
}
```

`ErrorState.tsx`:

```tsx
export default function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 px-6 py-8 text-center">
      <p className="text-sm text-red-700">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded-lg border border-red-300 px-4 py-2 text-sm text-red-700 transition hover:bg-red-100"
        >
          Thử lại
        </button>
      )}
    </div>
  );
}
```

**Không quét lại cả 15 trang.** Dùng ở trang mới và những trang vốn đã sửa vì responsive.

- [ ] **Step 2: Giấu câu nói với lập trình viên**

`web/app/checklist/page.tsx:66`:

```tsx
      setError(
        process.env.NODE_ENV === "development"
          ? "Không kết nối được backend. Chạy `uvicorn src.main:app --reload` chưa?"
          : "Không tải được checklist. Kiểm tra kết nối mạng rồi thử lại.",
      );
```

Trên production một cư dân mất mạng giây lát đang được bảo đi chạy uvicorn.

- [ ] **Step 3: Kiểm và commit**

```bash
cd web && npx tsc --noEmit && npm run build
git add web/app/components/EmptyState.tsx web/app/components/ErrorState.tsx web/app/checklist/page.tsx
git commit -m "feat(web): trạng thái rỗng/lỗi dùng chung, không lộ thông điệp nội bộ"
```

---

# Giai đoạn G — Guardrail (24–26/08)

Bốn task dưới đây **lấy yêu cầu từ `docs/ROLES_AND_PLAN.md` mục 13**, không phải từ spec của kế hoạch này. Ở đây chỉ xếp chỗ trong lịch và ghi tiêu chí xong.

## Task 18: Rate limiting (C3)

- [ ] Giới hạn theo IP trên `POST /chat` và các endpoint tải tệp. Xong khi: có test khẳng định request thứ N+1 trong cửa sổ trả 429; `README` ghi ngưỡng.
- [ ] Lý do không hoãn thêm: URL công khai, key trả tiền, hạn mức Google dùng chung cả nhóm — cạn thì `embed_query` chết theo và chat ngừng hoạt động.

## Task 19: Che PII trước khi ghi `chat_history` (E1)

- [ ] Che số CCCD, số điện thoại, email trong nội dung trước khi lưu. Xong khi: có test đưa vào chuỗi chứa số CCCD và khẳng định bản ghi trong DB đã bị che.

## Task 20: Partial unique index chống nộp trùng (E5)

- [ ] Index chỉ áp cho hồ sơ đang mở. Xong khi: migration chạy được cả hai chiều, và test khẳng định nộp trùng vẫn trả 409 (hiện đang kiểm ở tầng ứng dụng, index là chốt chặn ở tầng DB).

## Task 21: Log có cấu trúc + bắt lỗi tập trung (E4)

- [ ] Xong khi: một exception chưa bắt trả về JSON có mã lỗi thay vì stack trace, và log ra dòng JSON có `request_id`. **Không được in `DATABASE_URL` hay bất kỳ secret nào** — dùng `safe_database_url()`.

---

# Giai đoạn H — Tài liệu (27–28/08)

## Task 22: Đồng bộ tài liệu với mã nguồn (C4)

- [ ] `docs/PROJECT_CHARTER.md` — bỏ dòng `APPLICATIONS` là Phase 2 và "chưa migrate"; ghi US-08 và US-10 đã xong.
- [ ] `docs/architecture_diagram.md` — thêm 6 endpoint mới, cột `account_status`/`embed_status`, Chroma trên volume.
- [ ] `README.md` — 6 endpoint mới; ghi rằng `attachment.url` nay luôn `null` trong danh sách.
- [ ] `.env.example` — `rag_history_turns` và ba biến storage còn thiếu.
- [ ] Xong khi: đọc charter mà không thấy câu nào mâu thuẫn với `git log` hai tuần vừa rồi.

---

# Việc thuộc vai khác

Không viết bước chi tiết cho file của người khác. Ghi ở đây phần giao diện họ cần và tiêu chí xong, để không ai chờ nhầm.

## Thu (frontend)

| | Việc | Phụ thuộc | Xong khi |
|---|---|---|---|
| T1 | Đọc link ảnh qua `GET .../attachments/{id}/url` khi người dùng bấm mở | Task 1, 2 | Ảnh hiện lại được; không gọi sẵn cho cả danh sách |
| T2 | Trang `/bql/residents` (danh sách, lọc/tìm ở client từ `GET /admin/dashboard`) | Task 9 | Bấm một dòng vào được trang chi tiết |
| T3 | Trang `/bql/residents/{id}` — bốn khối: hồ sơ · checklist · hồ sơ đã nộp + giấy tờ thiếu · hành động | Task 8, 9 | Khoá/mở tài khoản và đặt lại mật khẩu chạy được từ đây |
| T4 | Trang `/bql/documents` — ô tiêu đề + ô dán nội dung, hiện `embed_status`, hỏi lại trạng thái | Task 15 | Nạp xong thấy trạng thái đổi từ `processing` sang `ready` |
| T5 | Màn hình "tài khoản bị khoá": bắt **403** sau đăng nhập, không phải 401 | Task 7 | Người bị khoá thấy thông báo rõ rồi bị đăng xuất, không phải màn hình trắng |
| T6 | Bỏ mở khoá tuần tự ở ô giấy tờ, dùng `missing_documents` | đã xong ở BE | Hiện đủ ô cùng lúc, đánh dấu đã có/còn thiếu |
| T7 | Gỡ `web/app/prototypes/action-card/` — trang thử nghiệm đang sống trên production | — | 404 |

⚠️ T6: khi xoá `REQUIRED_DOCUMENTS` khỏi `web/lib/applicationForms.ts:91-99`, **xoá luôn `getRequiredDocuments(taskName)` ở dòng 99**. Để lại một hàm dự phòng là làm sống lại đúng bảng chính sách trùng lặp mà việc này sinh ra để dẹp.

## Hải (AI)

| | Việc | Xong khi |
|---|---|---|
| H1 | Cho `ingest_file` nhận tài liệu do BQL gửi (Task 10 đã chốt ranh giới) | Endpoint ở Task 15 gọi được, nhịp batch/backoff không đổi |
| H2 | Đo lại `run_eval` | Có kết quả mới trong `eval/results/`. Số 32/35 đo 12/08 là **trước** khi có `rewrite_query` |
| H3 | V3 guard vùng biên + US-05 hiệu chỉnh ngưỡng | Câu "đúng lĩnh vực nhưng KB không có" không còn hiện trích dẫn dưới câu "tôi không biết" |
| H4 | V1 LangSmith | Có trace thật; hiện khai là deliverable ở 4 nơi mà `src/` không có dòng nào |
| H5 | Đo `run_eval` lần cuối **sau** H3 | Số trên slide đo trên đúng hệ thống đang chạy |

⚠️ H5 phải chạy **sau** H3. Đo trước rồi đổi ngưỡng là lặp lại đúng lỗi ngày 12/08: sửa graph mà không đo lại, nên suốt 6 ngày cả nhóm báo cáo một con số không còn đúng.

---

# Ngày 29/08 — đóng băng

Sau ngày này: **không đổi hạ tầng, không đổi hợp đồng API, không đổi ngưỡng RAG.** Chỉ sửa lỗi chặn demo, quay video, làm slide.

Đây là điều khoản có ràng buộc, không phải gợi ý. Mọi lần hỏng nặng của dự án đều đến từ thay đổi sát hạn mà không kịp đo lại.

## Nghiệm thu cuối trước Demo Day

- [ ] `pytest -q` xanh, `ruff check src/ tests/` sạch
- [ ] `cd web && npx tsc --noEmit && npm run build` sạch
- [ ] Mở toàn bộ luồng demo ở **390px** — không trang nào cuộn ngang ở cấp body
- [ ] `GET /health/deep` trả 200 và `chroma.documents` khớp số trước khi gắn volume
- [ ] Đăng nhập bằng tài khoản cư dân thật, chạy hết: onboarding → checklist → chat → nộp hồ sơ → tải ảnh → BQL duyệt
- [ ] Đăng nhập bằng tài khoản BQL, chạy hết: dashboard → chi tiết cư dân → khoá/mở → nạp tài liệu
- [ ] Ảnh dùng trong demo là ảnh giả hoặc đã che số — **không dùng CCCD thật của ai trong nhóm**
- [ ] Số eval trên slide đo **sau** lần đổi ngưỡng cuối cùng
