"""Nạp checklist template + dữ liệu cư dân giả vào DB.

Chạy:  python -m scripts.seed_data
       python -m scripts.seed_data --residents 100

(Phải chạy dạng `-m` từ thư mục gốc để import được `src`.)

Dữ liệu TẤT ĐỊNH (random seed cố định): cả nhóm chạy ra cùng một bộ, nên bug
kiểu "máy tôi thấy 6 mục, máy bạn thấy 7" là bug thật chứ không phải do data.

Hai điểm cần biết:

1. `conditions` của mọi checklist item được validate bằng CHÍNH rule engine
   (src/services/checklist.py). Gõ nhầm key -> script dừng ngay, thay vì để
   item im lặng không bao giờ khớp ai.

2. 8 cư dân đầu là hồ sơ dựng tay để phủ hết ma trận persona (chủ hộ/người thuê
   x có xe/không x gói tiện ích x đã/chưa onboarding). Phần còn lại random —
   random thuần không bảo đảm phủ được các nhánh hiếm.
"""

from __future__ import annotations

import argparse
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from src.config import get_settings, safe_database_url
from src.database import SessionLocal
from src.models.db import ChecklistCompletion, ChecklistItem, User
from src.services.checklist import matches, validate_conditions

SEED = 20260808

# Mã toà có thật ở Vinhomes Smart City, lấy từ data/kb/web/vsc-phi-dich-vu.md.
BUILDINGS = [
    "S101", "S102", "S103", "S105", "S106",
    "S201", "S202", "S203", "S205",
    "S301", "S302", "S303",
    "S401", "S402", "S403",
    "GS1", "GS2", "GS3", "GS5", "GS6",
    "I1", "I2", "I3", "I4", "I5",
]

APARTMENT_TYPES = ["studio", "1pn", "2pn", "3pn", "duplex"]
AMENITIES = ["pool", "gym", "tennis", "bbq", "kids_area"]

SURNAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Phan", "Vũ", "Võ",
    "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh",
]
MIDDLE_NAMES = ["Văn", "Thị", "Minh", "Quang", "Thu", "Hồng", "Đức", "Ngọc", "Anh", "Hải"]
GIVEN_NAMES = [
    "An", "Bình", "Cường", "Dũng", "Giang", "Hà", "Hạnh", "Hiếu", "Huy", "Khánh",
    "Lan", "Linh", "Mai", "Nam", "Phong", "Quân", "Sơn", "Thảo", "Trang", "Tuấn",
]

CHECKLIST_ITEMS = [
    {
        "task_name": "Ký nội quy toà nhà",
        "description": "Đọc và ký xác nhận nội quy sử dụng căn hộ tại văn phòng BQL.",
        "category": "Thủ tục chung",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 1,
    },
    {
        "task_name": "Làm thẻ cư dân (chủ hộ)",
        "description": "Nộp CCCD và giấy tờ chứng minh quyền sở hữu căn hộ, kèm ảnh 3x4.",
        "category": "Giấy tờ cư dân",
        "conditions": {"ownership_type": "owner"},
        "item_type": "bql_actionable",
        "order_index": 2,
    },
    {
        "task_name": "Làm thẻ cư dân (người thuê)",
        "description": "Nộp CCCD, hợp đồng thuê nhà và giấy uỷ quyền của chủ hộ, kèm ảnh 3x4.",
        "category": "Giấy tờ cư dân",
        "conditions": {"ownership_type": "renter"},
        "item_type": "bql_actionable",
        "order_index": 2,
    },
    {
        "task_name": "Đăng ký tạm trú tại công an phường",
        "description": (
            "Thủ tục này do cơ quan công an xử lý, không thuộc phạm vi BQL. "
            "Hướng dẫn dựa trên quy định công khai hiện hành."
        ),
        "category": "Cư trú",
        "conditions": {"ownership_type": "renter"},
        "item_type": "third_party_info",
        "order_index": 3,
    },
    {
        "task_name": "Cập nhật thông tin cư trú",
        "description": (
            "Cập nhật nơi thường trú mới qua VNeID hoặc công an phường. "
            "Không thuộc phạm vi BQL."
        ),
        "category": "Cư trú",
        "conditions": {"ownership_type": "owner"},
        "item_type": "third_party_info",
        "order_index": 3,
    },
    {
        "task_name": "Đăng ký thẻ xe",
        "description": "Đăng ký thẻ ra vào hầm gửi xe cho ô tô hoặc xe máy.",
        "category": "Phương tiện",
        "conditions": {"has_car": True},
        "item_type": "bql_actionable",
        "order_index": 4,
    },
    {
        "task_name": "Đăng ký chỗ đỗ xe cố định",
        "description": "Đăng ký vị trí đỗ xe theo tháng tại hầm B1-B3.",
        "category": "Phương tiện",
        "conditions": {"has_car": True},
        "item_type": "bql_actionable",
        "order_index": 5,
    },
    {
        "task_name": "Kích hoạt thẻ hồ bơi",
        "description": "Kích hoạt quyền sử dụng hồ bơi theo gói tiện ích đã đăng ký.",
        "category": "Tiện ích",
        "conditions": {"amenity_packages": "pool"},
        "item_type": "bql_actionable",
        "order_index": 6,
    },
    {
        "task_name": "Kích hoạt thẻ phòng gym",
        "description": "Kích hoạt quyền sử dụng phòng gym theo gói tiện ích đã đăng ký.",
        "category": "Tiện ích",
        "conditions": {"amenity_packages": "gym"},
        "item_type": "bql_actionable",
        "order_index": 7,
    },
    {
        "task_name": "Đăng ký thẻ thang máy",
        "description": "Kích hoạt thẻ thang máy theo tầng căn hộ.",
        "category": "Thủ tục chung",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 8,
    },
    {
        "task_name": "Đăng ký internet và truyền hình",
        "description": "Chọn nhà cung cấp trong danh sách được phép lắp đặt tại toà nhà.",
        "category": "Dịch vụ",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 9,
    },
    {
        "task_name": "Đăng ký chuyển đồ vào căn hộ",
        "description": "Đặt lịch dùng thang tải hàng và đăng ký thời gian chuyển đồ.",
        "category": "Thủ tục chung",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 10,
    },
]

# Phủ tay các nhánh mà random dễ bỏ sót: không tiện ích, đủ tiện ích,
# chưa onboarding, người thuê có xe, chủ hộ không xe.
FIXED_PROFILES = [
    {"ownership_type": "owner", "apartment_type": "2pn", "has_car": True,
     "amenity_packages": ["pool", "gym"]},
    {"ownership_type": "owner", "apartment_type": "3pn", "has_car": True,
     "amenity_packages": ["pool", "gym", "tennis", "bbq", "kids_area"]},
    {"ownership_type": "owner", "apartment_type": "studio", "has_car": False,
     "amenity_packages": []},
    {"ownership_type": "renter", "apartment_type": "1pn", "has_car": False,
     "amenity_packages": []},
    {"ownership_type": "renter", "apartment_type": "2pn", "has_car": True,
     "amenity_packages": ["gym"]},
    {"ownership_type": "renter", "apartment_type": "duplex", "has_car": True,
     "amenity_packages": ["pool"]},
    {"ownership_type": "owner", "apartment_type": "1pn", "has_car": False,
     "amenity_packages": ["kids_area"]},
    # Chưa onboarding: ownership_type = None -> chỉ khớp các item conditions rỗng.
    {"ownership_type": None, "apartment_type": None, "has_car": False,
     "amenity_packages": []},
]


def make_name(rng: random.Random) -> str:
    return " ".join(
        [rng.choice(SURNAMES), rng.choice(MIDDLE_NAMES), rng.choice(GIVEN_NAMES)]
    )


def make_email(name: str, index: int) -> str:
    ascii_name = (
        name.lower()
        .translate(str.maketrans("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ",
                                "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"))
        .replace(" ", ".")
    )
    return f"{ascii_name}{index}@moveinmate.demo"


def build_residents(rng: random.Random, count: int) -> list[User]:
    now = datetime.now(UTC)
    residents: list[User] = []

    for i in range(count):
        profile = (
            FIXED_PROFILES[i]
            if i < len(FIXED_PROFILES)
            else {
                "ownership_type": rng.choices(["owner", "renter", None], weights=[6, 3, 1])[0],
                "apartment_type": rng.choice(APARTMENT_TYPES),
                "has_car": rng.random() < 0.55,
                "amenity_packages": rng.sample(AMENITIES, rng.randint(0, 3)),
            }
        )
        if profile["ownership_type"] is None:
            # Chưa onboarding thì CHƯA khai gì cả — kể cả `has_car`. Thiếu dòng
            # này thì cư dân chưa điền form vẫn nhận mục "đăng ký thẻ xe", và
            # persona demo "chưa thiết lập hồ sơ" hiện 6 mục thay vì 4.
            profile = {
                **profile,
                "apartment_type": None,
                "amenity_packages": [],
                "has_car": False,
            }

        name = make_name(rng)
        residents.append(
            User(
                full_name=name,
                email=make_email(name, i + 1),
                phone=f"09{rng.randint(10_000_000, 99_999_999)}",
                building=rng.choice(BUILDINGS),
                apartment=f"{rng.randint(3, 38)}{rng.randint(1, 18):02d}",
                role="resident",
                onboarding_completed_at=(
                    None
                    if profile["ownership_type"] is None
                    else now - timedelta(days=rng.randint(1, 45))
                ),
                **profile,
            )
        )
    return residents


def build_completions(
    rng: random.Random, residents: list[User], items: list[ChecklistItem]
) -> list[ChecklistCompletion]:
    """Tick ngẫu nhiên một phần các mục KHỚP hồ sơ — để dashboard có tiến độ dở dang."""
    now = datetime.now(UTC)
    completions: list[ChecklistCompletion] = []

    for resident in residents:
        if resident.onboarding_completed_at is None:
            continue
        profile = {
            "ownership_type": resident.ownership_type,
            "apartment_type": resident.apartment_type,
            "has_car": resident.has_car,
            "amenity_packages": resident.amenity_packages,
        }
        eligible = [i for i in items if matches(profile, i.conditions)]
        done_count = rng.randint(0, len(eligible))
        for item in rng.sample(eligible, done_count):
            completions.append(
                ChecklistCompletion(
                    user_id=resident.user_id,
                    checklist_item_id=item.checklist_item_id,
                    completed_at=now - timedelta(days=rng.randint(0, 30)),
                )
            )
    return completions


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed dữ liệu demo cho MoveInMate")
    parser.add_argument("--residents", type=int, default=40, help="Số cư dân giả (mặc định 40)")
    args = parser.parse_args()

    if get_settings().app_env == "production":
        raise SystemExit("Từ chối seed khi APP_ENV=production.")

    for item in CHECKLIST_ITEMS:
        validate_conditions(item["conditions"])

    rng = random.Random(SEED)
    session = SessionLocal()
    try:
        session.execute(delete(ChecklistCompletion))
        session.execute(delete(ChecklistItem))
        session.execute(delete(User))
        session.flush()

        session.add_all([ChecklistItem(**item) for item in CHECKLIST_ITEMS])
        session.add(
            User(
                full_name="Ban quản lý Vinhomes Smart City",
                email="bql@moveinmate.demo",
                phone="02432505858",
                building="S101",
                apartment="BQL",
                role="admin",
                has_car=False,
                amenity_packages=[],
            )
        )
        residents = build_residents(rng, args.residents)
        session.add_all(residents)
        session.flush()

        items = list(session.scalars(select(ChecklistItem)))
        completions = build_completions(rng, residents, items)
        session.add_all(completions)
        session.commit()

        onboarded = sum(1 for r in residents if r.onboarding_completed_at)
        print(f"OK  {len(CHECKLIST_ITEMS)} checklist item")
        print(f"OK  1 tai khoan BQL + {len(residents)} cu dan ({onboarded} da onboarding)")
        print(f"OK  {len(completions)} luot tick checklist")
        print(f"    DB: {safe_database_url()}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
