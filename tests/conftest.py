import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from scripts.seed_data import CHECKLIST_ITEMS
from src.database import get_db
from src.main import app
from src.models.db import Base, ChecklistCompletion, ChecklistItem, User

# `sub` giả cho các test nhánh JWT. Unit test không ký được token ES256 thật,
# nên `verify_token` bị thay bằng bản giả trả thẳng UUID này — phần verify chữ
# ký đã được kiểm chứng riêng bằng token thật từ Supabase.
AUTH_UID_OWNER = uuid.UUID("11111111-1111-4111-8111-111111111111")


@pytest.fixture
def db_session():
    """DB SQLite in-memory, dựng lại từ đầu cho mỗi test.

    StaticPool giữ đúng một connection — SQLite in-memory sẽ mất sạch dữ liệu
    nếu mỗi lần truy vấn lại mở connection mới.

    Ba người dùng seed sẵn khớp với kịch bản demo:
    1 = BQL, 2 = chủ hộ đã onboarding, 3 = người thuê chưa onboarding.
    """
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()

    session.add_all([ChecklistItem(**item) for item in CHECKLIST_ITEMS])
    session.add_all(
        [
            User(
                user_id=1,
                full_name="Ban quản lý Smart City",
                email="bql@smartcity.demo",
                apartment="-",
                building="-",
                role="admin",
                has_car=False,
                amenity_packages=[],
            ),
            User(
                user_id=2,
                # Đã gắn tài khoản Supabase Auth — dùng cho test nhánh JWT.
                auth_user_id=AUTH_UID_OWNER,
                full_name="Trần Văn An",
                email="an.tran@demo.vn",
                apartment="S2.03-1512",
                building="Sapphire 2",
                role="resident",
                ownership_type="owner",
                apartment_type="2pn",
                has_car=True,
                amenity_packages=["pool"],
                onboarding_completed_at=datetime(2026, 8, 7, 9, 0, tzinfo=UTC),
            ),
            User(
                user_id=3,
                full_name="Lê Thị Bình",
                email="binh.le@demo.vn",
                apartment="S1.01-0803",
                building="Sapphire 1",
                role="resident",
                has_car=False,
                amenity_packages=[],
            ),
            # 4 và 5 tồn tại để test được phần cá nhân hóa: cùng đã onboarding
            # nhưng khác nhánh, nên checklist phải khác nhau.
            User(
                user_id=4,
                full_name="Ngô Minh Khánh",
                email="khanh.ngo@demo.vn",
                apartment="S2.01-2203",
                building="Sapphire 2",
                role="resident",
                ownership_type="renter",
                apartment_type="1pn",
                has_car=True,
                amenity_packages=["gym"],
                onboarding_completed_at=datetime(2026, 8, 7, 9, 0, tzinfo=UTC),
            ),
            User(
                user_id=5,
                full_name="Vũ Thu Trang",
                email="trang.vu@demo.vn",
                apartment="S3.03-0501",
                building="Sapphire 3",
                role="resident",
                ownership_type="owner",
                apartment_type="studio",
                has_car=False,
                amenity_packages=[],
                onboarding_completed_at=datetime(2026, 8, 7, 9, 0, tzinfo=UTC),
            ),
        ]
    )
    session.flush()
    session.add(ChecklistCompletion(user_id=2, checklist_item_id=1))
    session.commit()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """Async HTTP client — mọi request dùng chung DB in-memory của test."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


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


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch):
    """Chặn mọi lời gọi Supabase Storage trong test.

    `autouse` chứ không phải chọn thủ công: `_attachment_dict` ký signed URL
    mỗi lần đọc hồ sơ, nên bất kỳ test nào chạm tới hồ sơ có tệp đính kèm cũng
    sẽ bắn request thật nếu quên bật fixture. Cùng bài học với
    `fake_auth_provisioning` — test lỡ gọi dịch vụ ngoài đã phải đi dọn tay
    một lần rồi (11/08).

    Giữ nguyên `build_object_path` và `display_name`: hai hàm này thuần, không
    chạm mạng, và chính chúng là thứ cần được kiểm.
    """
    from src.services import storage

    uploaded: dict[str, bytes] = {}

    def _upload(path: str, data: bytes, _content_type: str) -> None:
        uploaded[path] = data

    monkeypatch.setattr(storage, "upload", _upload)
    monkeypatch.setattr(storage, "signed_url", lambda path: f"https://fake.test/{path}")
    monkeypatch.setattr(storage, "ensure_bucket", lambda: None)
    return uploaded
