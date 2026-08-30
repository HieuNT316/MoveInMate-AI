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
from typing import Any

from sqlalchemy import delete, select

from src.config import get_settings, safe_database_url
from src.database import SessionLocal
from src.models.db import ChecklistCompletion, ChecklistItem, User
from src.services.checklist import matches, validate_conditions
from src.services.documents import DOCUMENT_LABELS

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

ROUTING_FIELDS = ("handling_department", "submission_location", "processing_time")


def validate_routing(item: dict[str, Any]) -> None:
    """Mục BQL xử lý được thì PHẢI có đủ ba trường định tuyến, mục ngoài phạm vi
    thì KHÔNG được có trường nào.

    Thiếu bước này thì thêm một mục checklist mới mà quên dữ liệu định tuyến sẽ
    dựng ra một nút "Nộp hồ sơ" không biết gửi đi đâu — cùng loại lỗi im lặng mà
    `validate_conditions` đang chặn.
    """
    present = [f for f in ROUTING_FIELDS if item.get(f)]

    if item["item_type"] == "bql_actionable" and len(present) != len(ROUTING_FIELDS):
        missing = sorted(set(ROUTING_FIELDS) - set(present))
        raise ValueError(f"{item['task_name']!r} thiếu định tuyến: {missing}")

    if item["item_type"] == "third_party_info" and present:
        raise ValueError(
            f"{item['task_name']!r} là thủ tục ngoài phạm vi BQL nhưng lại có "
            f"định tuyến: {sorted(present)}"
        )


def validate_documents(item: dict[str, Any]) -> None:
    """Mã giấy tờ phải nằm trong bảng nhãn, và thủ tục ngoài phạm vi BQL thì
    không được khai giấy tờ bắt buộc.

    Vì sao mục `third_party_info` để rỗng: KB đòi CT01 *hoặc* ảnh VNeID, mà
    phép đối chiếu là AND — ép một loại cụ thể sẽ báo "thiếu" sai cho người đã
    nộp bằng cách hợp lệ khác. Ràng buộc "phải có ít nhất một ảnh mới ghi nhận
    được" đã canh phần này rồi.
    """
    codes = item.get("required_documents") or []

    unknown = sorted(set(codes) - set(DOCUMENT_LABELS))
    if unknown:
        raise ValueError(f"{item['task_name']!r} dùng mã giấy tờ lạ: {unknown}")

    if item["item_type"] == "third_party_info" and codes:
        raise ValueError(
            f"{item['task_name']!r} ngoài phạm vi BQL nhưng lại khai giấy tờ "
            f"bắt buộc: {codes}"
        )


def validate_sla(item: dict[str, Any]) -> None:
    """Thủ tục ngoài phạm vi BQL thì KHÔNG được khai thời hạn xử lý.

    Cùng lý do với `validate_routing`: khai một con số SLA cho thủ tục do công an
    phường xử lý là mạo nhận cam kết của cơ quan khác, và report sẽ đếm hồ sơ đó
    vào tỉ lệ đúng hạn của BQL — sai cả hai đầu.

    `bql_actionable` được phép để None: có thủ tục BQL nhận nhưng thời hạn nằm
    ngoài tầm kiểm soát (lịch nhà mạng). Không ép có số ở đây, vì ép thì người
    thêm mục mới sẽ bịa một con số cho qua.
    """
    sla = item.get("sla_business_days")

    if item["item_type"] == "third_party_info" and sla is not None:
        raise ValueError(
            f"{item['task_name']!r} ngoài phạm vi BQL nhưng lại khai "
            f"sla_business_days={sla}"
        )

    if sla is not None and sla < 1:
        raise ValueError(f"{item['task_name']!r} có sla_business_days={sla}, phải >= 1")


# Category mà `src/services/badges.py` dựa vào để biết hồ sơ nào trao huy hiệu
# thẻ cư dân / thẻ xe. Dùng category thay vì tên thủ tục hay id: tên có biến thể
# ("(chủ hộ)" / "(người thuê)"), còn id đổi sau mỗi lần seed vì hàm này xoá và
# tạo lại toàn bộ bảng.
BADGE_CATEGORIES = ("Giấy tờ cư dân", "Phương tiện")


def validate_badge_categories(items: list[dict[str, Any]]) -> None:
    """Category mà badge dựa vào phải thật sự tồn tại trong seed.

    Gõ sai một chữ thì badge im lặng không bao giờ được trao — đúng lớp lỗi mà
    `validate_conditions` sinh ra để chặn cho rule engine.
    """
    present = {item.get("category") for item in items}
    missing = sorted(set(BADGE_CATEGORIES) - present)
    if missing:
        raise ValueError(
            f"Category cho badge không có mục checklist nào dùng: {missing}. "
            f"Sửa BADGE_CATEGORIES hoặc src/services/badges.py cho khớp."
        )


CHECKLIST_ITEMS = [
    {
        "task_name": "Ký nội quy toà nhà",
        "required_documents": ["cccd"],
        "description": "Đọc và ký xác nhận nội quy sử dụng căn hộ tại văn phòng BQL.",
        "category": "Thủ tục chung",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 1,
        "handling_department": "Lễ tân & CSKH",
        "submission_location": "Quầy lễ tân tầng 1",
        "processing_time": "Trong ngày",
        "sla_business_days": 1,
    },
    {
        "task_name": "Làm thẻ cư dân (chủ hộ)",
        "required_documents": ["cccd", "bien_ban_ban_giao"],
        "description": "Nộp CCCD và giấy tờ chứng minh quyền sở hữu căn hộ, kèm ảnh 3x4.",
        "category": "Giấy tờ cư dân",
        "conditions": {"ownership_type": "owner"},
        "item_type": "bql_actionable",
        "order_index": 2,
        "handling_department": "Lễ tân & CSKH",
        "submission_location": "Quầy lễ tân tầng 1",
        "processing_time": "1–3 ngày làm việc",
        "sla_business_days": 3,
    },
    {
        "task_name": "Làm thẻ cư dân (người thuê)",
        # KB ghi giấy uỷ quyền là ĐIỀU KIỆN ("nếu BQL yêu cầu" —
        # data/kb/web/vsc-the-cu-dan.md:54, và 3 chỗ khác nói tương tự).
        # Liệt kê như bắt buộc thì mọi người thuê nộp đủ CCCD + hợp đồng
        # vẫn bị báo thiếu — đúng lỗi mà D1 sinh ra để tránh.
        "required_documents": ["cccd", "hop_dong_thue"],
        "description": "Nộp CCCD, hợp đồng thuê nhà và giấy uỷ quyền của chủ hộ, kèm ảnh 3x4.",
        "category": "Giấy tờ cư dân",
        "conditions": {"ownership_type": "renter"},
        "item_type": "bql_actionable",
        "order_index": 2,
        "handling_department": "Lễ tân & CSKH",
        "submission_location": "Quầy lễ tân tầng 1",
        "processing_time": "1–3 ngày làm việc",
        "sla_business_days": 3,
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
        # Mục 3 trong KB là lựa chọn (biên bản bàn giao HOẶC hợp đồng thuê) nên
        # bỏ — phép đối chiếu là AND, không diễn đạt được "hoặc".
        "required_documents": ["cccd", "dang_ky_xe", "the_cu_dan"],
        "description": "Đăng ký thẻ ra vào hầm gửi xe cho ô tô hoặc xe máy.",
        "category": "Phương tiện",
        "conditions": {"has_car": True},
        "item_type": "bql_actionable",
        "order_index": 4,
        "handling_department": "An ninh",
        "submission_location": "Quầy lễ tân tầng 1",
        "processing_time": "1–2 ngày làm việc",
        "sla_business_days": 2,
    },
    {
        "task_name": "Đăng ký chỗ đỗ xe cố định",
        "required_documents": ["cccd", "the_xe", "don_dang_ky"],
        "description": "Đăng ký vị trí đỗ xe theo tháng tại hầm B1-B3.",
        "category": "Phương tiện",
        "conditions": {"has_car": True},
        "item_type": "bql_actionable",
        "order_index": 5,
        "handling_department": "An ninh",
        "submission_location": "Quầy lễ tân tầng 1",
        "processing_time": "2–5 ngày làm việc",
        "sla_business_days": 5,
    },
    {
        # Tên phải khớp bảng định tuyến trong data/kb/bql/bql-co-cau-va-quy-trinh.md.
        # Trước 13/08 mục này tên "hồ bơi" còn KB dùng "bể bơi" ở cả 10 chỗ —
        # lệch tên là hồ sơ không tra được bộ phận xử lý.
        "task_name": "Kích hoạt thẻ bể bơi",
        "required_documents": ["cccd", "the_cu_dan"],
        "description": "Kích hoạt quyền sử dụng bể bơi theo gói tiện ích đã đăng ký.",
        "category": "Tiện ích",
        "conditions": {"amenity_packages": "pool"},
        "item_type": "bql_actionable",
        "order_index": 6,
        "handling_department": "Quản lý tiện ích chung",
        "submission_location": "Quầy lễ tân tầng 1",
        "processing_time": "Trong ngày",
        "sla_business_days": 1,
    },
    {
        "task_name": "Kích hoạt thẻ phòng gym",
        "required_documents": ["cccd", "the_cu_dan"],
        "description": "Kích hoạt quyền sử dụng phòng gym theo gói tiện ích đã đăng ký.",
        "category": "Tiện ích",
        "conditions": {"amenity_packages": "gym"},
        "item_type": "bql_actionable",
        "order_index": 7,
        "handling_department": "Quản lý tiện ích chung",
        "submission_location": "Quầy lễ tân tầng 1",
        "processing_time": "Trong ngày",
        "sla_business_days": 1,
    },
    {
        "task_name": "Đăng ký thẻ thang máy",
        "required_documents": ["cccd", "the_cu_dan"],
        "description": "Kích hoạt thẻ thang máy theo tầng căn hộ.",
        "category": "Thủ tục chung",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 8,
        "handling_department": "An ninh",
        "submission_location": "Quầy lễ tân tầng 1",
        "processing_time": "Trong ngày",
        "sla_business_days": 1,
    },
    {
        "task_name": "Đăng ký internet và truyền hình",
        "description": "Chọn nhà cung cấp trong danh sách được phép lắp đặt tại toà nhà.",
        "category": "Dịch vụ",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 9,
        "handling_department": "Kỹ thuật (hỗ trợ lắp đặt)",
        "submission_location": "Quầy lễ tân tầng 1",
        "processing_time": "Theo lịch nhà mạng",
        # KHÔNG có SLA: lịch do nhà mạng đặt, BQL chỉ hỗ trợ lắp đặt. Đặt một
        # con số ở đây là tự bịa cam kết thay cho bên thứ ba.
        "sla_business_days": None,
    },
    {
        "task_name": "Đăng ký chuyển đồ vào căn hộ",
        "required_documents": ["cccd", "don_dang_ky"],
        "description": "Đặt lịch dùng thang tải hàng và đăng ký thời gian chuyển đồ.",
        "category": "Thủ tục chung",
        "conditions": {},
        "item_type": "bql_actionable",
        "order_index": 10,
        "handling_department": "Lễ tân & CSKH",
        "submission_location": "Quầy lễ tân tầng 1",
        "processing_time": "Đặt trước 24 giờ",
        # KHÔNG có SLA: "đặt trước 24 giờ" là hạn cư dân phải báo TRƯỚC, không
        # phải thời gian BQL xử lý. Đo đúng hạn theo con số này sẽ sai nghĩa.
        "sla_business_days": None,
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
        validate_routing(item)
        validate_documents(item)
        validate_sla(item)
    validate_badge_categories(CHECKLIST_ITEMS)

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
                # BQL không nhận nhà nên không có onboarding. Vẫn đặt mốc này
                # vì frontend dùng `onboarding_completed_at is null` làm tín
                # hiệu chuyển hướng: để trống thì đăng nhập BQL bị đẩy vào form
                # onboarding của cư dân — mà form đó nay đã 403.
                # Cách sạch hơn là frontend rẽ theo `role` (việc của vai FE).
                onboarding_completed_at=datetime.now(UTC),
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
