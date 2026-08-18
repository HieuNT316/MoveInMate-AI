# Thiết kế — Trải nghiệm người dùng & Console Ban quản lý

> Lập **18/08/2026**, sau GATE 2. Nguồn: nhận xét của mentor tại buổi demo —
> *"UI/UX cũng như trải nghiệm người dùng chưa đủ tốt, các tính năng quản lý
> dành cho ban quản lý cần làm rõ ràng, chi tiết hơn."*
>
> Trạng thái: **đã duyệt** (Hiếu, 18/08). Thay thế phần phân bổ công việc của
> `docs/ROLES_AND_PLAN.md` mục 13; ba mốc thời gian ở mục đó vẫn giữ nguyên.
>
> Kế hoạch triển khai: `docs/superpowers/plans/2026-08-18-ux-va-console-bql.md`

## 1. Vấn đề

Mentor nhận xét chung, không chỉ đích danh màn hình nào. Nên phần chẩn đoán
dưới đây là kết quả đo trên mã nguồn ngày 18/08, không phải suy đoán từ lời
nhận xét.

### 1.1 Ứng dụng không dùng được trên điện thoại

| Đo được | Con số |
|---|---|
| Class responsive (`sm:`/`md:`/`lg:`) trong toàn bộ ~3.300 dòng TSX | **18** |
| File có bất kỳ class responsive nào / tổng số file | **6 / 20** |
| Nav mobile, hamburger, drawer | không có |
| Toast / phản hồi sau thao tác | không có dòng nào |

`web/app/components/Sidebar.tsx:47` là `w-72 shrink-0 h-screen` — 288px cứng,
không breakpoint — nằm trong `flex h-screen overflow-hidden`. Trên màn 390px,
sidebar chiếm 288px, còn ~100px cho nội dung, và không có cách nào thu lại.
`BQLSidebar.tsx:58` y hệt.

`web/app/manifest.ts` khai `display: "standalone"`. Sản phẩm đang được phát
hành như một app cài vào điện thoại, trong khi giao diện chỉ chạy trên desktop.
Cư dân nhận nhà dùng điện thoại, không mở laptop.

Các lỗi nhỏ hơn cùng nhóm: `dashboard/page.tsx:199` có `<table>` không bọc
`overflow-x` nên tràn ngang; `chat/page.tsx:401` có panel `w-64` cứng;
`chat/page.tsx:191` dùng `h-[calc(100vh-9rem)]` — `100vh` sai trên mobile vì
thanh địa chỉ trình duyệt ăn mất phần đáy.

### 1.2 Khu BQL nông, không phải xấu

`BQLSidebar.tsx:30-38` khai 2 mục hoạt động và 2 mục xám khoá "Sắp có". Ai mở
khu quản lý cũng thấy một nửa là ổ khoá.

Hai trang đang chạy đều là bảng phẳng và **không nối được với nhau**:
`/bql/dashboard` liệt kê cư dân kèm % tiến độ, `/bql/applications` liệt kê hồ
sơ. BQL không bấm được vào một cư dân để xem người đó vướng mục nào, đã nộp gì,
thiếu giấy tờ nào. Dữ liệu đã có đủ ở backend; chưa ai ráp lại thành một trang.

### 1.3 Phản hồi thao tác không nhất quán, và có chỗ lộ thông điệp nội bộ

Mỗi trang tự giữ một `error` state và tự vẽ khối lỗi riêng.
`checklist/page.tsx:66` hiển thị cho người dùng cuối dòng: *"Không kết nối được
backend. Chạy `uvicorn src.main:app --reload` chưa?"* — câu nói với lập trình
viên, xuất hiện trên production khi mạng chập chờn.

### 1.4 Ký URL đính kèm chặn event loop

`src/services/store.py:307` gọi `storage.signed_url()` cho **mỗi tệp đính kèm,
mỗi lần đọc hồ sơ**. `src/services/storage.py:101` là `httpx.post` **đồng bộ**,
timeout 30 giây, nằm trong route `async def`.

Hệ quả hai tầng: N tệp = N lượt gọi mạng tuần tự trước khi trang hiện; và vì là
lời gọi đồng bộ trong hàm async, nó chặn event loop nên **mọi request của mọi
người khác đều phải đợi**.

Hiện production chỉ có 5 tệp nên chưa đau. Nhưng trang chi tiết cư dân (mục 4)
nạp toàn bộ hồ sơ của một người cùng lúc, và bước chuẩn bị dữ liệu demo sẽ bơm
thêm tệp — đúng cái trang khuếch đại lỗi này lên nhất.

### 1.5 Chroma trên production là bộ nhớ tạm

`src/services/vectorstore.py` ghi vào `persist_directory` — thư mục trên đĩa
container. `docs/DEPLOY.md:211` đã ghi sẵn: *"Chroma đang nướng thẳng vào
image"*, chưa gắn volume. Tài liệu nạp trên production sẽ mất ở lần deploy kế
tiếp. Đây là rào cản thật của US-08.

## 2. Mục tiêu

1. Ứng dụng dùng được trên điện thoại, đúng như manifest đang tuyên bố.
2. Khu BQL có chiều sâu: từ một cư dân xem được toàn bộ tình trạng của họ và
   thao tác được lên tài khoản đó.
3. Mọi thao tác thay đổi dữ liệu đều có phản hồi nhìn thấy được.
4. BQL tự nạp được tài liệu vào tri thức của trợ lý, và tài liệu đó **không
   biến mất sau deploy**.
5. Trả nốt các guardrail đã khai với BTC mà mã nguồn chưa có.

### Không phải mục tiêu

- Thiết kế lại nhận diện thị giác. Giữ nguyên bảng token màu hiện có.
- Dựng hạ tầng test tự động cho `web/`.
- US-09 CRUD FAQ — đã bỏ từ trước, giữ nguyên quyết định.
- Luồng mời qua email thay mật khẩu tạm — sẽ làm mất khả năng đăng nhập của cả
  41 tài khoản demo (`src/services/supabase_admin.py` đã ghi lý do từ lúc dựng).
- Đọc PDF cho US-08.
- Thông báo đẩy, lịch sử chuyển trạng thái, xoá tệp đã tải — đã khai là ngoài
  phạm vi ở `docs/CONTRACT_US13.md` mục 8.

## 3. Lớp vỏ responsive

**Quyết định: một cơ chế duy nhất — thanh tab đáy, dùng chung cho cả hai khu**,
mỗi layout truyền mảng menu của mình vào.

Lý do không chọn drawer + hamburger: khu cư dân có đúng 4 mục menu, khu BQL sẽ
có 4 mục. Bốn mục vừa khít một thanh tab, nên không cần drawer, không cần lớp
phủ, không cần quản lý trạng thái đóng/mở. Drawer là giải pháp cho menu dài; ở
đây không có menu dài. Với PWA khai `display: standalone`, thanh tab đáy cũng
là thứ khiến sản phẩm đọc ra như một app thay vì một trang web bị bóp lại.

| File | Thay đổi |
|---|---|
| `web/app/lib/nav.ts` | **Tạo mới** — chuyển hai mảng `menus` ra khỏi hai sidebar |
| `web/app/components/MobileTabBar.tsx` | **Tạo mới** — `fixed bottom-0 inset-x-0 lg:hidden`, nhận `items` |
| `Sidebar.tsx:47`, `BQLSidebar.tsx:58` | thêm `hidden lg:flex` |
| `Layout.tsx`, `BQLLayout.tsx` | `main` → `px-4 py-6 pb-24 lg:px-8 lg:py-10 lg:pb-10`; gắn tab bar |
| `Header.tsx` | `h-20 px-8` → `h-16 px-4 lg:h-20 lg:px-8`; ẩn phụ đề dưới `lg` |
| `ChatWidget.tsx:86` | `hidden lg:block` |
| `chat/page.tsx:401` | panel hội thoại `w-64` → `hidden lg:flex` |
| `chat/page.tsx:191` | thêm nhánh `100dvh` cho mobile, giữ `100vh` cho desktop |
| `dashboard/page.tsx:199` | bọc bảng trong `overflow-x-auto` |

Ba chi tiết bắt buộc:

**Nút chat nổi phải ẩn hẳn trên mobile, không phải đẩy lên.** Nó ở
`fixed bottom-6 right-6 z-50`, đè đúng thanh tab. Đổi thành `bottom-24` sẽ tạo
hai lối vào chat cạnh nhau, trong khi tab "AI Chat" đã làm việc đó.

**`100vh` sai trên mobile.** Dùng `100dvh` cho nhánh mobile; giữ `100vh` cho
desktop để không đụng thứ đang chạy đúng.

**Tách `menus` ra `lib/nav.ts` trước khi dựng tab bar.** Nếu sidebar và tab bar
mỗi bên giữ một bản danh sách, sớm muộn chúng lệch nhau — đúng cái bẫy
`REQUIRED_DOCUMENTS` mà D1 vừa dẹp xong.

## 4. Trang chi tiết cư dân

### 4.1 Endpoint

`GET /api/v1/admin/residents/{user_id}`, bảo vệ bằng `require_admin`.

```python
class ResidentDetailResponse(BaseModel):
    profile: ProfileResponse
    checklist: ChecklistResponse
    applications: list[ApplicationResponse]
    account_status: AccountStatus
```

Cố ý **ghép ba schema đã có** thay vì bịa schema phẳng mới: frontend đã có
component render `ChecklistResponse` và `ApplicationResponse` ở khu cư dân, nên
trang BQL dùng lại được, không viết lại logic hiển thị.

Dùng `ApplicationResponse` chứ không phải `AdminApplicationResponse` — đã biết
đang xem ai thì ba trường `user_id`/`full_name`/`apartment` là thừa.

Phần backend gần như không phải viết mới: `_build_checklist(db, user)` trong
`src/api/routes.py` đã tồn tại và nhận vào một dict hồ sơ.

**Quy tắc 404:** id không tồn tại **hoặc** `role != "resident"` đều trả 404. Cho
phép mở chi tiết một tài khoản BQL sẽ hiện một checklist nhận nhà vô nghĩa —
đúng lỗi mà `require_resident` sinh ra để chặn.

**Không thêm endpoint danh sách.** `GET /admin/dashboard` đã trả toàn bộ cư dân
kèm tiến độ `bql_scope`. Trang danh sách dùng lại nó; 41 cư dân thì lọc và tìm
kiếm làm ở client, không cần tham số server.

### 4.2 Nối hai bảng phẳng

Bấm một dòng ở `/bql/dashboard`, hoặc bấm tên cư dân ở `/bql/applications`, đều
dẫn vào `/bql/residents/{id}`. Trang gồm bốn khối: hồ sơ · checklist đang vướng
ở đâu · hồ sơ đã nộp kèm giấy tờ thiếu · hành động lên tài khoản (mục 5).

### 4.3 Ký URL theo yêu cầu — đổi hợp đồng

Bỏ `url` khỏi phản hồi danh sách; thêm:

`GET /api/v1/applications/{application_id}/attachments/{attachment_id}/url`

Frontend gọi khi người dùng thật sự mở ảnh. Số lượt ký từ N xuống thường là 0,
vì phần lớn lượt xem hồ sơ không ai bấm vào ảnh nào.

Đây là **thay đổi hợp đồng**: frontend đang đọc `attachment.url` trực tiếp. Phải
cập nhật `docs/CONTRACT_US13.md` và báo Thu trước khi code — charter mục 12 yêu
cầu chốt bằng văn bản đúng những chỗ như thế này.

**Giữ trường `url` trong schema nhưng luôn trả `null` ở phản hồi danh sách** qua
một nhịp deploy. Ảnh không hiện thì tốt hơn trang vỡ vì thiếu trường.

Endpoint mới phục vụ **cả cư dân lẫn BQL**, nên dùng `get_current_user` chứ
không phải `require_resident` — gắn `require_resident` sẽ khoá BQL ra khỏi chính
những ảnh họ cần đối chiếu. Quyền kiểm trong thân hàm, theo **cả hai** khoá:

1. tệp phải thuộc đúng `application_id` trong đường dẫn (nếu không → 404);
2. hồ sơ phải thuộc đúng người gọi, **hoặc** người gọi có `role == "admin"`.

Kiểm thiếu khoá thứ nhất thì đoán được id tệp của người khác là đọc được ảnh
CCCD của họ. Đây đúng lỗi mà bản review của D1 đã bắt trên endpoint gán loại
giấy tờ; không lặp lại.

**Bảo mật:** trang này là nơi ảnh CCCD/VNeID hiện ra cho BQL — hợp lệ, vì đối
chiếu giấy tờ là việc của họ. Giữ bucket private, URL sống 5 phút, không ghi URL
ra log.

## 5. Khoá tài khoản & đặt lại mật khẩu

### 5.1 Cột `account_status`

Khai kiểu dùng chung trong `src/models/schemas.py`:

```python
AccountStatus = Literal["active", "locked"]
```

Cột trên bảng `users`: mặc định `active`, NOT NULL.

Migration nối tiếp revision `4b4ea98a4e85` theo nếp đã dùng 4 lần: **thêm
nullable → backfill `'active'` → mới khoá NOT NULL**. Autogenerate luôn sinh
thẳng `nullable=False` không kèm server default và luôn vỡ trên bảng đã có dữ
liệu.

Kiểm tra đặt trong `get_current_user`, áp cho **cả hai nhánh** JWT lẫn
`X-User-Id`. Chỉ chặn nhánh JWT thì trên môi trường dev tài khoản bị khoá vẫn
dùng được, mà bản demo chạy đúng nhánh đó.

Thông điệp 403: `"Tài khoản đã bị Ban quản lý tạm khoá"`.

### 5.2 Hai endpoint

| Endpoint | Thân | Trả về |
|---|---|---|
| `PATCH /api/v1/admin/residents/{user_id}/status` | `{"account_status": "locked"}` | `ResidentDetailResponse` |
| `POST /api/v1/admin/residents/{user_id}/reset-password` | — | `{"temporary_password": "..."}` |

Cả hai dùng chung quy tắc 404 của mục 4.1 (không tồn tại **hoặc** không phải cư
dân). Quy tắc đó gánh luôn hai việc: BQL không tự khoá được mình, và không khoá
được BQL khác.

`PATCH .../status` trả về **toàn bộ** `ResidentDetailResponse` chứ không riêng
trường vừa đổi, theo đúng nếp của `PATCH /checklist/{item_id}`: giao diện cập
nhật cả trang trong một lượt gọi, không phải tự suy ra trạng thái mới rồi lệch
với server.

Đặt lại mật khẩu cần thêm `update_auth_password(auth_user_id, password)` trong
`src/services/supabase_admin.py`, gọi `PUT /admin/users/{id}`. Lỗi:

- **409** khi `auth_user_id` là `None` — cư dân có hồ sơ nhưng chưa được cấp tài
  khoản đăng nhập thì không có mật khẩu nào để đặt lại. Không phải trường hợp lý
  thuyết: `seed_data` xoá sạch `auth_user_id`, ai chạy seed mà quên
  `provision_auth` là rơi vào đúng đó.
- **502** khi Supabase từ chối hoặc không gọi tới được (khớp nếp của
  `create_auth_user`).

### 5.3 `fake_auth_provisioning` chuyển thành `autouse`

Hiện là fixture tự chọn, vì trước giờ chỉ một test tạo tài khoản. Giờ sẽ có
nhiều hơn, và hậu quả của việc quên nặng hơn hẳn: test sẽ gọi thật vào Supabase
Admin API và **đổi mật khẩu của một tài khoản có thật trên production**. So với
sự cố 11/08 — chỉ đẻ ra một user thừa rồi đi xoá tay — cái này không dọn lại
được, người bị đổi mật khẩu mất quyền đăng nhập. Đây đúng là lý do
`fake_storage` được để `autouse`.

Fixture phải chặn cả `create_auth_user` lẫn `update_auth_password`.

### 5.4 Hệ quả phản trực giác mà frontend phải xử

Khoá tài khoản **chỉ chặn ở backend, không đụng Supabase Auth**. Người bị khoá
vẫn **đăng nhập thành công** và vẫn nhận JWT hợp lệ, nhưng mọi lời gọi API sau
đó trả 403.

Giao diện phải xử đúng luồng: đăng nhập xong → gọi `/profile` → nhận 403 kèm
`detail` là *"Tài khoản đã bị Ban quản lý tạm khoá"* → hiện màn hình báo khoá rồi
đăng xuất. Nếu chỉ bắt 401, người bị khoá sẽ thấy màn hình trắng.

Không dùng `ban_duration` của Supabase: thêm một lời gọi mạng, thêm một trạng
thái nằm ngoài DB của mình, và mở khoá thì phải đồng bộ hai nơi.

### 5.5 Nơi trường này hiện ra

Thêm `account_status` vào `ResidentProgress` (danh sách) và
`ResidentDetailResponse` (chi tiết). **Không** thêm vào `ProfileResponse`: cư dân
bị khoá không gọi nổi `/profile`, nên trường đó vĩnh viễn chỉ có giá trị
`active`.

## 6. US-08 — BQL tự nạp tài liệu

### 6.1 Đính chính về hạn mức embedding

`_EMBED_BATCH_SIZE = 15` trong `src/services/ingest.py`: mỗi lời gọi API gửi 15
chunk. Một tài liệu quy trình vài trang chừng 30 chunk, tức **2 lời gọi** trên
hạn mức 1000/ngày — không đáng kể. Ngưỡng mà đoạn code đó né là **~100
chunk/phút**, là giới hạn *tốc độ*, không phải hạn mức ngày.

Ghi lại đính chính này vì lập luận "US-08 rủi ro vì quota" từng được nêu và nó
không đứng vững. Rào cản thật là mục 1.5.

### 6.2 Gắn Railway Volume

Gắn volume vào `/app/data/chroma`. `docs/DEPLOY.md:211` đã chỉ đúng cách này.
Làm **sớm trong tuần**, không để ngày 31/08 — đây là thay đổi hạ tầng trên bản
production đang chạy, cần thời gian để lộ ra nếu hỏng.

**Chế độ hỏng phải sợ nhất:** volume mới gắn thì rỗng. Container khởi động với
Chroma rỗng → `rag_retrieve` không trả về gì → guard chống bịa kích hoạt ở **mọi
câu hỏi** → trợ lý từ chối trả lời toàn bộ, mà không có màn hình nào báo lỗi và
mọi chỉ báo vẫn xanh. Đúng kiểu sự cố 11/08.

Hai thứ đi kèm, không tách rời:

- **Seed lúc khởi động**: volume rỗng thì chép bản nằm trong image vào trước khi
  phục vụ request đầu tiên.

  ⚠️ **Bản trong image không thể nằm ở chính `/app/data/chroma`** — volume mount
  che khuất đường dẫn đó, nội dung image ở đấy sẽ không nhìn thấy được. Dockerfile
  phải chép KB đã ingest vào một đường dẫn khác, ví dụ `/app/data/chroma_seed`,
  và bước seed chép từ đó sang. Bỏ sót chi tiết này thì volume vĩnh viễn rỗng và
  rơi thẳng vào chế độ hỏng vừa mô tả.
- **`/health/deep`** (V4/E2) kiểm DB + `collection.count()`, trả 503 khi thành
  phần chết. Ở bản kế hoạch trước, E2 bị xếp là việc biên và hoãn được. Quyết
  định đó **đảo lại**: một khi Chroma nằm trên volume có thể rỗng,
  `collection.count()` là thứ duy nhất phân biệt "hệ thống khoẻ" với "hệ thống
  câm".

### 6.3 Phạm vi: dán nội dung, không tải PDF

`ingest_file` chỉ nhận `.md` **có frontmatter YAML hợp lệ**; BQL không gõ YAML.
Endpoint tự sinh frontmatter từ form: `title` do BQL nhập, `source_type` cố định
là `bql_internal`.

Giao diện là một ô nhập tiêu đề cộng một ô dán nội dung. Dễ demo hơn tải tệp, và
không phải viết bộ phân tích PDF.

### 6.4 Embed chạy nền

15 chunk mỗi lượt, nghỉ 12 giây — tài liệu 30 chunk mất khoảng nửa phút, tài
liệu dài mất vài phút. Không thể làm trong một HTTP request.

Dùng `BackgroundTasks`; thêm cột `embed_status` trên bảng `documents` với bốn
giá trị `pending` · `processing` · `ready` · `failed`; giao diện hỏi lại trạng
thái. Container chết giữa chừng thì bản ghi kẹt ở `processing` và BQL bấm nạp
lại — đủ cho phạm vi này, không dựng hàng đợi.

### 6.5 Ranh giới vai — chốt với Hải trước khi code

`ingest` thuộc vai AI (`CLAUDE.md`). Chia:

- **Hải**: cho `ingest_file` nhận được tài liệu do BQL gửi; xác nhận hành vi
  nhịp/thử lại vẫn đúng khi gọi từ tiến trình web.
- **Hiếu**: endpoint, cột `embed_status`, gắn volume, seed lúc khởi động,
  `/health/deep`.

Charter mục 12 bắt chốt bằng văn bản trước khi hai vai code song song. Đây là
việc **đầu tiên** của phần này, không phải việc làm sau.

Nhắc lại bẫy đã biết: `data/chroma/` là DB nhị phân nằm trong git. Chỉ vai AI
chạy `ingest_kb`. Chỉ **đọc** Chroma cũng làm bẩn `.bin`/`.sqlite3` →
`git checkout -- data/chroma/` để dọn, **nhưng không bao giờ làm thế ngay sau khi
ingest** (đã xoá mất kết quả ngày 11/08). Sau mọi thao tác git đụng thư mục này,
kiểm `collection.count()`.

## 7. Lớp phản hồi

### 7.1 Toast

`ToastProvider` + `useToast()` đặt ở `web/app/layout.tsx`, tự viết, khoảng 60
dòng. Không thêm thư viện: cần đúng một hình dạng thông báo, và nó phải dùng
bảng token màu sẵn có (`bg-gold`, `text-ink`, `border-border`) — thư viện ngoài
mang giao diện riêng rồi phải đi ghi đè. Thêm phụ thuộc vào bundle của PWA 14
ngày trước demo cũng không đáng.

Danh sách đóng các thao tác sẽ có phản hồi: tick mục checklist · nộp hồ sơ · tải
ảnh minh chứng · BQL đổi trạng thái hồ sơ · BQL gán loại giấy tờ · khoá/mở tài
khoản · đặt lại mật khẩu · nạp tài liệu.

### 7.2 `EmptyState` và `ErrorState`

Dựng component dùng chung, nhưng **không quét lại cả 15 trang** — `CLAUDE.md`
mục 3 cấm sửa thứ không hỏng. Dùng ở các trang mới (danh sách cư dân, chi tiết
cư dân, tài liệu) và những trang vốn đã phải sửa vì responsive. Phần còn lại
thay dần khi có người đụng tới.

### 7.3 Không lộ thông điệp nội bộ

`checklist/page.tsx:66` chuyển câu *"Chạy `uvicorn src.main:app --reload` chưa?"*
vào sau `process.env.NODE_ENV === "development"`. Người dùng thấy câu bình
thường; khi phát triển vẫn thấy gợi ý cũ.

## 8. Phân công và thứ tự

Chia vai đã chốt: **Hiếu làm lớp nền giao diện** (vỏ responsive, toast,
empty/error state) **và toàn bộ backend**; **Thu dựng trang**; **Hải giữ phần
AI**. Chia theo lớp chứ không theo thư mục, nên hai người ít đụng cùng file.

**Bốn việc trong lịch dưới đây KHÔNG được thiết kế lại ở tài liệu này** — rate
limiting (C3), che PII trước khi ghi `chat_history` (E1), partial unique index
chống nộp trùng hồ sơ (E5), log có cấu trúc + bắt lỗi tập trung (E4). Chúng giữ
nguyên phạm vi đã mô tả ở `docs/ROLES_AND_PLAN.md` mục 13; ở đây chỉ xếp chỗ
trong lịch. Kế hoạch triển khai lấy yêu cầu từ mục 13, không phải từ tài liệu
này.

### Bốn ràng buộc thứ tự

1. **Đổi hợp đồng ký-theo-yêu-cầu đi trước nhất** — không phải vì khó, mà vì Thu
   cần thời gian dài nhất để phản ứng. Báo trước rồi mới code.
2. **Vỏ responsive xong trước khi Thu dựng trang mới.** Ngược lại thì trang mới
   chỉ chạy trên desktop và phải sửa lần hai.
3. **Gắn volume làm sớm**, là thay đổi rủi ro nhất.
4. **`account_status` trước trang chi tiết cư dân**, vì nó là một trường trong
   phản hồi đó.

### Lịch

| Ngày | Việc |
|---|---|
| 18–19/08 | Báo Thu đổi hợp đồng · ký theo yêu cầu · vỏ responsive · `account_status` |
| 20–21/08 | Chi tiết cư dân · volume + seed + `/health/deep` · Thu dựng `/bql/residents` |
| 22–23/08 | Nạp tài liệu (Hiếu + Hải) · toast/empty/error · Thu dựng trang tài liệu |
| 24–26/08 | Rate limit · che PII · unique index · log có cấu trúc · Hải: đo lại eval, guard vùng biên, LangSmith |
| 27–28/08 | Cập nhật tài liệu · chạy thử · sửa lỗi phát sinh |
| **29/08** | **Đóng băng** — không đổi hạ tầng, không đổi hợp đồng nữa |
| 30–31/08 | Quay video · slide · đo eval lần cuối chốt số |
| 01/09 | Demo Day |

Ngày đóng băng là điều khoản có ràng buộc. Mọi lần hỏng nặng của dự án đều đến
từ thay đổi sát hạn mà không kịp đo lại.

## 9. Rủi ro

| | Rủi ro | Chặn bằng |
|---|---|---|
| R1 | Volume rỗng → trợ lý câm toàn bộ, mọi chỉ báo vẫn xanh | Seed lúc khởi động + `/health/deep` + kiểm `collection.count()` sau mỗi lần deploy |
| R2 | Thao tác git làm bẩn `data/chroma/` | `git checkout -- data/chroma/` sau khi **đọc**, nhưng không bao giờ ngay sau ingest |
| R3 | Đổi hợp đồng làm vỡ trang của Thu giữa tuần | Giữ trường `url` trong schema, trả `null` ở danh sách một nhịp deploy |
| R4 | Số eval trên slide lại là số cũ | Đo lại **sau** khi đổi ngưỡng, không phải trước. Đúng lỗi đã mắc 12/08 |
| R5 | Migration chạy lúc container khởi động trên dữ liệu thật | Thử `upgrade` và `downgrade` trên bản sao dữ liệu đã có trước khi đẩy |

## 10. Cách nghiệm thu

**Backend** — TDD: `pytest -q && ruff check src/ tests/`. Mỗi endpoint mới có
test cho đường thành công, 403 sai vai, 404 sai đối tượng.

**Frontend** — `cd web && npx tsc --noEmit && npm run build`, rồi kiểm tay ở
**390px · 768px · 1280px**. `web/` không có test tự động; phần này là checklist
thủ công, và dựng hạ tầng test FE nằm ngoài phạm vi 14 ngày còn lại.

**Deploy** — kiểm bằng dấu hiệu nội dung lấy từ mã nguồn hiện tại, không dùng
header `Age`. Đã hai lần kết luận sai "chưa deploy" vì tìm chuỗi không tồn tại và
vì tin vào `Age`.

## 11. Ràng buộc toàn cục

Áp cho mọi task, chép từ `CLAUDE.md` và các quyết định đã chốt:

- **Không in secret ra stdout.** `DATABASE_URL` chứa mật khẩu; dùng
  `safe_database_url()`. Repo có hook đẩy log lên server chấm điểm.
- **`DATABASE_URL` trong `.env` trỏ vào Supabase production thật.** Không chạy
  `seed_data` hay alembic lên nó.
- **Test không được gọi dịch vụ ngoài.** Fixture `fake_auth_provisioning` và
  `fake_storage`. Test chạy trên SQLite in-memory với `StaticPool`.
- **Không PATCH hồ sơ tài khoản demo** — dữ liệu seed là tất định.
- **Giấy tờ tuỳ thân không bao giờ được embed vào Chroma.** Bucket private, URL
  ký ngắn hạn. Demo dùng ảnh giả hoặc đã che số.
- **`SUPABASE_SERVICE_KEY` chỉ dùng ở backend**, bỏ qua toàn bộ RLS.
- **Định tuyến hồ sơ và phân loại cư dân dùng rule-based, không LLM.**
- **`sources[]` sinh tất định từ `rag_retrieve`**; guard chống bịa nằm trong
  code, không trong prompt.
- **Lệnh `railway` phải chạy từ PowerShell**; `railway up` đóng gói thư mục hiện
  tại, không phải commit — `git status` trước.
- Trên Windows, tiếng Việt trong stdout cần `PYTHONIOENCODING=utf-8`.
- `ruff check --fix scripts/` sẽ sửa cả script logging của BTC — chỉ chạy trên
  file mình sửa.
