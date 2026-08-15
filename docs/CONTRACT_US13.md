# Hợp đồng API — US-13 nộp hồ sơ trực tuyến

> Chốt trước khi code, theo `PROJECT_CHARTER.md` mục 12. Backend: Hiếu. Giao
> diện: Thu. **Thu không cần đợi backend chạy xong** — hình dạng dữ liệu dưới
> đây là cam kết, có thể mock ngay.
>
> Trạng thái: **đề xuất** (13/08). Thu xác nhận hoặc phản hồi trước khi Hiếu
> khoá hợp đồng.

## 1. Ý tưởng

Thay vì cầm giấy tờ tới quầy lễ tân, cư dân bấm nộp ngay từ mục checklist. Hệ
thống tự định tuyến hồ sơ tới **đúng bộ phận** phụ trách thủ tục đó, và cư dân
theo dõi được hồ sơ đang ở bước nào.

Định tuyến **tất định**, tra từ bảng trong `data/kb/bql/bql-co-cau-va-quy-trinh.md`,
**không hỏi LLM** — cùng lý do đã áp cho rule engine checklist: thủ tục hành
chính cần đúng tuyệt đối và giải thích được.

## 2. Hai ranh giới không được nhầm

**Nộp hồ sơ ≠ tick checklist.** Nộp là gửi yêu cầu đi; tick là tự xác nhận đã
xong. Cư dân nộp hồ sơ xong mục checklist **vẫn chưa** được đánh dấu hoàn thành —
chỉ khi BQL chuyển trạng thái sang *Đã trả kết quả* thì mới coi là xong, và việc
tick vẫn do cư dân tự làm.

**Hai loại hồ sơ khác bản chất** *(cập nhật 15/08 — thay quy tắc "thủ tục ngoài
phạm vi trả 400" ở bản trước)*. Mọi mục checklist đều nộp được, nhưng backend tự
gắn `kind` theo thủ tục, client không khai được:

| | `bql_processing` | `self_declared` |
|---|---|---|
| Ví dụ | Thẻ xe, thẻ cư dân | Tạm trú, cập nhật cư trú |
| Ai xử lý | Bộ phận BQL | Không ai — cư dân tự khai |
| Định tuyến | Có bộ phận | `null` cả ba trường |
| BQL làm gì | Tiếp nhận → xử lý → trả kết quả | Chỉ **ghi nhận** |
| Ảnh minh chứng | Tuỳ chọn | **Bắt buộc** — chính là nội dung nộp |

⚠️ **Giao diện tuyệt đối không hiện "Ban quản lý đang xử lý hồ sơ tạm trú của
bạn"** với `self_declared` — sai sự thật, và phá nguyên tắc sản phẩm không mạo
nhận quy trình của cơ quan khác. Dùng chữ kiểu *"Đã gửi minh chứng, chờ Ban quản
lý ghi nhận"*.

Backend chặn sẵn: BQL **không** chuyển được hồ sơ `self_declared` sang *Đã duyệt*
hay *Đã trả kết quả* khi chưa có ảnh nào (**409**).

## 3. Trường mới trên checklist item

`GET /api/v1/checklist` giữ nguyên hình dạng cũ, mỗi item có thêm ba trường:

```jsonc
{
  "id": 30,
  "task_name": "Đăng ký thẻ xe",
  "item_type": "bql_actionable",
  "handling_department": "An ninh",              // null với third_party_info
  "submission_location": "Quầy lễ tân tầng 1",   // null với third_party_info
  "processing_time": "1–2 ngày làm việc"         // null với third_party_info
}
```

Ba trường này đủ để hiện dòng **"Bộ phận · Nơi nộp · Thời hạn"** ngay trong
checklist, kể cả khi cư dân chưa nộp gì.

## 4. Sáu trạng thái

Bám đúng quy trình đã mô tả trong KB, không tự đặt thêm:

| Mã | Nhãn hiển thị |
|---|---|
| `received` | Đã tiếp nhận |
| `processing` | Đang xử lý |
| `needs_info` | Cần bổ sung |
| `approved` | Đã duyệt |
| `delivered` | Đã trả kết quả |
| `rejected` | Từ chối |

Backend trả **mã**; nhãn tiếng Việt do giao diện quyết định.

## 5. Endpoint

### `POST /api/v1/applications` — cư dân nộp

```jsonc
// gửi
{ "checklist_item_id": 30, "note": "Xe biển 30A-123.45" }   // note tuỳ chọn

// nhận 201
{
  "application_id": 7,
  "checklist_item_id": 30,
  "task_name": "Đăng ký thẻ xe",
  "status": "received",
  "handling_department": "An ninh",
  "submission_location": "Quầy lễ tân tầng 1",
  "processing_time": "1–2 ngày làm việc",
  "note": "Xe biển 30A-123.45",
  "bql_note": null,
  "created_at": "2026-08-13T10:00:00Z",
  "updated_at": "2026-08-13T10:00:00Z"
}
```

Lỗi: **400** mục ngoài phạm vi BQL · **404** mục không có trong checklist của
chính người này · **409** đã có hồ sơ đang mở cho đúng mục đó.

### `GET /api/v1/applications` — cư dân xem hồ sơ của mình

Mảng các object như trên, mới nhất trước.

### `GET /api/v1/admin/applications` — BQL xem tất cả

Như trên, thêm `user_id`, `full_name`, `apartment`. Lọc tuỳ chọn:
`?status=received` và `?department=An ninh`.

### `PATCH /api/v1/admin/applications/{id}` — BQL đổi trạng thái

```jsonc
{ "status": "needs_info", "bql_note": "Thiếu bản sao đăng ký xe" }
```

Trả về object đã cập nhật. `bql_note` tuỳ chọn.

## 6. Điều Thu cần biết để làm giao diện

- Nút **"Nộp hồ sơ"** chỉ hiện ở mục `item_type = "bql_actionable"`.
- Nút điều hướng trong chat (`suggested_action`) đang dẫn tới
  `/checklist?item=<id>` — giữ nguyên, không đổi.
- Một mục chỉ có **một hồ sơ đang mở**. Đã nộp thì thay nút bằng trạng thái
  hiện tại.
- `needs_info` và `rejected` là hai trạng thái cần làm nổi bật — cư dân phải
  hành động tiếp; `bql_note` giải thích thiếu gì.

## 7. Tải ảnh minh chứng

Tách khỏi `POST /applications` để không phá phần hợp đồng đã chốt: tạo hồ sơ
bằng JSON như cũ, **rồi** đính tệp.

### `POST /api/v1/applications/{id}/attachments`

`multipart/form-data`, một tệp mỗi lần, field tên `file`.

```jsonc
// nhận 201
{
  "attachment_id": 3,
  "filename": "vneid.png",
  "content_type": "image/png",
  "size_bytes": 184320,
  "url": "https://…/object/sign/…",   // ĐỌC TẠM THỜI, hết hạn sau 5 phút
  "uploaded_at": "2026-08-15T10:00:00Z"
}
```

Giới hạn: **5MB**, chỉ nhận `image/jpeg` · `image/png` · `application/pdf`.

Lỗi: **404** hồ sơ không tồn tại hoặc không phải của mình · **415** sai định
dạng · **413** quá lớn · **400** tệp rỗng · **502** lưu trữ lỗi.

Mọi hồ sơ trả về đều có `attachments: []` với cùng hình dạng trên.

### Hai điều FE cần nhớ

**`url` hết hạn sau 5 phút** — ký lại mỗi lần đọc hồ sơ. Đừng cache vào
localStorage hay share ra ngoài; tải lại trang là có link mới.

**Đây là giấy tờ tuỳ thân** (CCCD, VNeID). Bucket private, không có URL công
khai. Đừng hiện ảnh ở trang nào không kiểm đăng nhập, đừng ghi ra log.
**Khi demo dùng ảnh giả hoặc đã che số**, không dùng CCCD thật của ai trong nhóm.

## 8. Chưa làm ở lát này

Không thông báo đẩy, không lịch sử chuyển trạng thái (chỉ giữ trạng thái hiện
tại), không xoá tệp đã tải lên. Ghi ra để khỏi ai chờ nhầm.
