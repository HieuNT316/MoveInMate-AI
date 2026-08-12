# MoveInMate — hướng dẫn cho AI agent

Trợ lý AI hướng dẫn cư dân làm thủ tục nhận nhà ở Vinhomes Smart City.
Khách hàng là **Ban quản lý**; cư dân là người dùng cuối được BQL cấp tài khoản.

## Đọc gì trước khi sửa

| Câu hỏi | File | |
|---|---|---|
| Phạm vi, quyết định đã chốt, timeline | `docs/PROJECT_CHARTER.md` | **nguồn sự thật — mâu thuẫn thì file này thắng** |
| Thiết kế kỹ thuật, hợp đồng API | `docs/architecture_diagram.md` | |
| Trải nghiệm sản phẩm | `docs/PRD.md` | |
| Ai làm gì | `docs/ROLES_AND_PLAN.md` | |
| Deploy | `docs/DEPLOY.md` | |
| Quan sát, guardrail | `docs/OPERATIONS.md` | |

**Định nghĩa thuật ngữ bằng tài liệu, không bằng code đang có.** Ngày 11/08 một
agent định nghĩa "agent điều hướng" từ tool tình cờ tồn tại, bỏ sót US-13 nằm
cùng file — và ghi mâu thuẫn đó thẳng vào charter.

Vai trò: **Hiếu** BE+Data · **Hải** AI (`src/agents/`, ingest, prompt) · **Thu** FE (`web/`).
Đụng ranh giới giữa hai vai thì chốt bằng văn bản trước khi code (charter mục 12).

## Lệnh

```bash
python -m scripts.seed_data          # KHÔNG phải python scripts/seed_data.py
python -m scripts.provision_auth     # cấp tài khoản Supabase, chạy sau seed
python -m scripts.check_db           # chẩn đoán DATABASE_URL
python -m scripts.run_eval           # 35 câu, tốn 35 lượt embedding
pytest -q && ruff check src/ tests/  # CI chỉ quét src/ và tests/
```

Trên Windows, tiếng Việt trong stdout cần `PYTHONIOENCODING=utf-8`, nếu không
sẽ `UnicodeEncodeError`.

**Lệnh `railway` phải chạy từ PowerShell.** CLI lưu liên kết theo đường dẫn
`D:\...`; Git Bash đứng ở `/d/...` nên báo "No linked project found" dù liên kết
vẫn còn. `railway up` đóng gói **thư mục hiện tại**, không phải commit — `git
status` trước.

## Sáu cái bẫy đã gây thiệt hại thật

**1. `data/chroma/` là DB nhị phân nằm trong git.**
Chỉ **vai AI** chạy `ingest_kb`; người khác chỉ pull. Thêm file `.md` vào
`data/kb/` thì thoải mái — chỉ bước embed là dành riêng.
Chỉ **đọc** Chroma cũng làm bẩn `.bin` và `.sqlite3` → `git checkout -- data/chroma/`
để dọn. **Nhưng đừng làm thế ngay sau khi ingest** — sẽ xoá mất kết quả (đã xảy
ra 11/08). Sau mọi thao tác git đụng thư mục này, kiểm `collection.count()`.
Dấu hiệu index hỏng: `count()` vẫn đúng, metadata đọc được, nhưng
`get(include=["embeddings"])` lỗi `Error finding id`.

**2. Hạn mức embedding Google: 1000 request/ngày, tính theo _project_.**
Key mới trong cùng tài khoản **không** có quota mới. Bản deploy và máy mọi người
dùng chung. Cạn thì `embed_query` cũng chết → chat ngừng hoạt động.

**3. Supabase có ba chuỗi kết nối, chỉ một dùng được.**
Dùng **Session pooler** (cổng 5432, host `pooler`). Direct chỉ có IPv6; Transaction
pooler cổng 6543 làm Alembic lỗi. `check_db.py` bắt cả ba trường hợp.

**4. Đừng PATCH hồ sơ tài khoản demo.**
Dữ liệu seed là **tất định** để cả nhóm thấy giống nhau. Test PATCH đã làm trôi 9
trường, mất cả hai persona "chưa onboarding" của kịch bản demo. Lỡ thì:
`python -m scripts.seed_data` rồi `python -m scripts.provision_auth`
(seed xoá `auth_user_id`, không gắn lại thì không ai đăng nhập được).

**5. Test không được gọi dịch vụ ngoài.**
Một test tạo tài khoản đã đẻ user thật trong Supabase và phải đi dọn tay. Dùng
fixture `fake_auth_provisioning`. Test chạy trên SQLite in-memory với `StaticPool`.

**6. Không in secret ra stdout.**
`DATABASE_URL` chứa mật khẩu. Dùng `safe_database_url()`. Repo có hook tự động
đẩy log lên server chấm điểm.

## Bất biến thiết kế — phá là hỏng sản phẩm

- **`sources[]` sinh tất định từ `rag_retrieve`**, không hỏi LLM. Đây là cách yêu
  cầu "trích tài liệu" thành bảo đảm kỹ thuật thay vì lời dặn trong prompt.
- **Guard chống bịa nằm trong code**, không trong prompt: `retrieved` rỗng thì
  `generate` **không gọi LLM**.
- **Phân loại cư dân và định tuyến hồ sơ dùng rule-based, không LLM.** Thủ tục
  hành chính cần đúng tuyệt đối và giải thích được. Việc gì tính tất định được thì
  đừng giao cho LLM — nút điều hướng từng phụ thuộc LLM gọi tool và đo được **0/5**.
- **Key của `conditions` phải nằm trong `PROFILE_FIELDS`** (`src/services/checklist.py`).
  Gõ sai thì mục checklist im lặng không khớp ai. `seed_data` validate lúc nạp.
- **Checklist lọc trực tiếp mỗi lần xem**, chỉ lưu mục đã xong.
- **`X-User-Id` chỉ là lối dev**, bị chặn khi `APP_ENV=production`. Không có nó thì
  ai cũng đặt header của BQL để thành BQL.
- **`seed_data` từ chối chạy khi `APP_ENV=production`** — chốt an toàn có chủ đích.
- **Dữ liệu tự sinh mang `source_type: synthetic_demo`** và hiện nhãn "Quy trình mô
  phỏng" ở UI. **Số liệu phí phải trích nguồn công khai**, không tự đặt.

## Trước khi commit

```bash
ruff check src/ tests/ && pytest -q
git checkout -- data/chroma/     # nếu đã chạy gì đó đọc Chroma
git status                        # đừng commit thay đổi ngoài phạm vi việc đang làm
```

Frontend: `cd web && npx tsc --noEmit && npm run build`.

`ruff check --fix scripts/` sẽ sửa cả script logging của BTC — đừng chạy trên cả
thư mục, chỉ chạy trên file mình sửa.
