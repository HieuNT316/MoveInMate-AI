"""Tạo hồ sơ mẫu để màn hình BQL và báo cáo có số liệu lúc demo.

VÌ SAO CẦN: `seed_data` chỉ dựng cư dân và checklist. Nó xoá `users` +
`checklist_items`, mà `applications` có FK CASCADE tới cả hai — nên sau mỗi lần
seed, bảng `applications` rỗng và màn hình BQL hiện `total = 0`, mọi ô báo cáo
để trống. Đúng thiết kế ("thiếu dữ liệu trả None"), nhưng demo trông như sản
phẩm chưa ai dùng.

CÁCH LÀM: đi qua đúng `store.create_application` và
`store.update_application_status` như một request thật, KHÔNG INSERT thô. Nhờ
vậy dữ liệu chạy qua mọi guard, và mỗi lần đổi trạng thái sinh một dòng
`audit_log` — đó là NGUỒN DUY NHẤT để `reports.py` biết hồ sơ vào trạng thái
nào lúc nào. INSERT thẳng vào `applications` sẽ cho ra bảng có số nhưng
`avgProcessingDays` và `onTimeRate` vẫn None.

MỐC THỜI GIAN: `audit_log.created_at` để `server_default=now()`, nên sau khi
tạo xong phải lùi ngày lại — không lùi thì mọi hồ sơ đều "xử lý trong 0 ngày"
và `trends[]` dồn hết vào hôm nay.

TẤT ĐỊNH: `random.Random(SEED)` cố định, chạy lại cho cùng kết quả. Cùng lý do
với `scripts/seed_data.py`.

Chạy:  python -m scripts.seed_demo_applications
"""

from __future__ import annotations

import random
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from src.config import get_settings, safe_database_url
from src.database import SessionLocal
from src.models.db import Application, ChecklistItem, User
from src.services import store

SEED = 20260831

# (mã thủ tục, trạng thái cuối, số ngày trước đây lúc NỘP, số ngày xử lý)
#
# Trải trên 25 ngày để `trends[]` có nhiều điểm. Số ngày xử lý đặt quanh SLA
# của từng thủ tục để `onTimeRate` ra một con số THẬT — không phải 100% (nhìn
# như bịa) cũng không phải 0%.
#
#   49 Ký nội quy            SLA 1 ngày
#   50 Thẻ cư dân (chủ hộ)   SLA 3 ngày
#   51 Thẻ cư dân (người thuê) SLA 3
#   54 Đăng ký thẻ xe        SLA 2
#   55 Chỗ đỗ xe cố định     SLA 5
#   56 Thẻ bể bơi            SLA 1
#   58 Thẻ thang máy         SLA 1
KICH_BAN = [
    # Đã trả kết quả, đúng hạn
    (50, "delivered", 24, 2),
    (49, "delivered", 22, 1),
    (54, "delivered", 20, 1),
    (56, "delivered", 18, 1),
    (51, "delivered", 16, 3),
    (58, "delivered", 14, 1),
    # Đã trả kết quả, TRỄ hạn — để onTimeRate không phải 100%
    (50, "delivered", 21, 6),
    (54, "delivered", 15, 5),
    (55, "delivered", 12, 9),
    # Đã duyệt, chờ trả kết quả
    (51, "approved", 9, 2),
    (56, "approved", 7, 1),
    # Bị từ chối
    (54, "rejected", 17, 3),
    # Đang xử lý / cần bổ sung / vừa tiếp nhận — phần "đang mở" của dashboard
    (55, "processing", 6, None),
    (50, "needs_info", 5, None),
    (49, "processing", 3, None),
    (57, "received", 2, None),
    (60, "received", 1, None),
    (59, "needs_info", 4, None),
]

GHI_CHU_BQL = {
    "needs_info": "Ảnh CCCD bị mờ ở phần số, cư dân vui lòng chụp lại rõ nét.",
    "rejected": "Hợp đồng thuê đã hết hiệu lực từ tháng trước.",
    "delivered": "Đã trả kết quả tại quầy lễ tân tầng 1.",
    "approved": "Hồ sơ hợp lệ, đang chờ in thẻ.",
}


def _lui_thoi_gian(db, application_id: int, ngay_nop: datetime, ngay_xong: datetime | None):
    """Lùi mốc thời gian của hồ sơ và các dòng audit tương ứng.

    Phải lùi cả hai: `applications.created_at` cho dashboard, và
    `audit_log.created_at` cho `_first_reached` trong `reports.py`. Thiếu vế
    audit thì `avgProcessingDays` vẫn None dù bảng có dữ liệu.
    """
    db.execute(
        text("UPDATE applications SET created_at = :t, updated_at = :u WHERE application_id = :i"),
        {"t": ngay_nop, "u": ngay_xong or ngay_nop, "i": application_id},
    )
    if ngay_xong is not None:
        db.execute(
            text(
                "UPDATE audit_log SET created_at = :t "
                "WHERE resource_type = 'application' AND resource_id = :i"
            ),
            {"t": ngay_xong, "i": application_id},
        )


def main() -> None:
    settings = get_settings()
    if settings.app_env == "production":
        raise SystemExit("Từ chối tạo dữ liệu mẫu khi APP_ENV=production.")

    rng = random.Random(SEED)
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.role == "admin"))
        if admin is None:
            raise SystemExit("Chưa có tài khoản BQL — chạy `python -m scripts.seed_data` trước.")

        # Chỉ lấy cư dân ĐÃ onboarding: người chưa onboarding là hai persona
        # dành riêng cho việc quay cảnh điền form (xem kịch bản video), đụng
        # vào là hỏng cảnh đó.
        cu_dan = list(
            db.scalars(
                select(User)
                .where(User.role == "resident", User.onboarding_completed_at.is_not(None))
                .order_by(User.user_id)
            )
        )
        if len(cu_dan) < 5:
            raise SystemExit("Không đủ cư dân đã onboarding.")

        items = {i.checklist_item_id: i for i in db.scalars(select(ChecklistItem))}
        now = datetime.now(UTC)
        da_dung = set()  # (user_id, item_id) — tránh đụng index chống nộp trùng
        tao_duoc = 0

        for ma_item, trang_thai, ngay_truoc, ngay_xu_ly in KICH_BAN:
            item = items.get(ma_item)
            if item is None:
                continue

            nguoi = next(
                (u for u in rng.sample(cu_dan, len(cu_dan)) if (u.user_id, ma_item) not in da_dung),
                None,
            )
            if nguoi is None:
                continue
            da_dung.add((nguoi.user_id, ma_item))

            kind = "bql_processing" if item.item_type == "bql_actionable" else "self_declared"
            app = store.create_application(
                db,
                user_id=nguoi.user_id,
                checklist_item_id=ma_item,
                kind=kind,
                note="Hồ sơ mẫu phục vụ demo.",
            )
            app_id = app["application_id"]

            ngay_nop = now - timedelta(days=ngay_truoc)
            ngay_xong = None

            if ngay_xu_ly is not None:
                # Đi qua `update_application_status` để sinh audit_log thật.
                store.update_application_status(
                    db,
                    app_id,
                    trang_thai,
                    GHI_CHU_BQL.get(trang_thai),
                    None,
                    performed_by=admin.user_id,
                )
                ngay_xong = ngay_nop + timedelta(days=ngay_xu_ly)
            elif trang_thai != "received":
                store.update_application_status(
                    db, app_id, trang_thai, GHI_CHU_BQL.get(trang_thai), None,
                    performed_by=admin.user_id,
                )

            _lui_thoi_gian(db, app_id, ngay_nop, ngay_xong)
            tao_duoc += 1

        db.commit()

        tong = db.scalar(select(Application).with_only_columns(Application.application_id))
        so_audit = db.execute(text("SELECT count(*) FROM audit_log")).scalar()
        print(f"OK  {tao_duoc} hồ sơ mẫu")
        print(f"OK  {so_audit} dòng audit_log (nguồn mốc thời gian cho báo cáo)")
        print(f"    DB: {safe_database_url()}")
        if tong is None:
            print("    (cảnh báo: không đọc lại được hồ sơ nào)", file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    main()
