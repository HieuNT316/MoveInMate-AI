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
    monkeypatch.setattr(
        storage,
        "generate_signed_url",
        lambda bucket, path, expires_in=900: f"https://fake.test/{path}",
    )
    monkeypatch.setattr(storage, "ensure_bucket", lambda: None)
    return uploaded


@pytest.fixture(autouse=True)
def fake_ingest(monkeypatch, db_session):
    """Chặn embed thật VÀ chặn kết nối DB thật của job nạp tài liệu nền.

    `POST /admin/documents` chạy `_embed_document` trong `BackgroundTasks`.
    Hàm đó tự mở `SessionLocal()` vì session của request đã đóng lúc job nền
    chạy — và `SessionLocal` KHÔNG đi qua `app.dependency_overrides[get_db]`
    mà fixture `client` dùng. `httpx.ASGITransport` CHẠY background task thật
    trước khi trả response, nên nếu không patch ở đây, `SessionLocal()` sẽ nối
    thẳng `DATABASE_URL` thật (Supabase PRODUCTION trong `.env` của repo này)
    và `ingest_file` thật sẽ gọi Google embedding API — ghi hàng thật vào
    production và tiêu hạn mức 1000 request/ngày dùng chung cả nhóm. Cùng bài
    học sự cố 11/08 khiến `fake_auth_provisioning`/`fake_storage` là autouse.

    `autouse=True` như hai fixture trên: hậu quả quên gắn nặng hơn hẳn một
    test lỡ tay, không thể để tuỳ chọn.

    Patch trên MODULE `routes` (`from src.api import routes`), KHÔNG patch
    `src.services.ingest.ingest_file` hay `src.database.SessionLocal`:
    `routes.py` import hai tên này ở mức module (`from src.services.ingest
    import ingest_file` / `from src.database import SessionLocal`), nên
    `routes.ingest_file` và `routes.SessionLocal` là hai tham chiếu riêng đã
    bind sẵn — patch ở module nguồn sẽ không đổi được thứ `routes.py` gọi.

    `SessionLocal` giả trỏ THẲNG vào `db_session` — CHÍNH session mà fixture
    `client` dùng qua `get_db` — chứ không phải một DB in-memory rời rạc như
    bản trước. Bản trước (round 1) dùng DB rời để giữ fixture nhẹ, không ép
    `db_session` lên mọi test trong bộ; nhưng hậu quả là mọi lượt
    `set_embed_status` của job nền ghi vào một DB không ai đọc lại được —
    `pending -> processing -> ready/failed` không có test nào QUAN SÁT được,
    nên xoá hẳn `_embed_document` vẫn không làm assertion nào đỏ. Task 14/15
    tồn tại chính vì state machine này, nên "không kiểm được" = không kiểm.
    Đổi lại trỏ về `db_session` thật để trạng thái ghi ra observable được từ
    test, đánh đổi lấy việc `fake_ingest` giờ kéo `db_session` vào MỌI test
    trong bộ (kể cả test không đụng DB) — chấp nhận được vì SQLite in-memory
    dựng lại rất rẻ, và cái giá đó nhỏ hơn nhiều so với một state machine
    không kiểm chứng được.

    `with SessionLocal() as db:` trong `_embed_document` gọi `__exit__` khi
    thoát khối — với một session THẬT được tự mở riêng thì đóng ở đó là đúng,
    nhưng ở đây `SessionLocal()` trả về CHÍNH `db_session` dùng chung cho cả
    phần còn lại của test, nên đóng nó sẽ phá mọi truy vấn SAU khi job nền
    chạy (kể cả GET tiếp theo trong cùng test). `_NonClosingSession` bọc
    `db_session` trong một context manager nuốt `close()`, chỉ nhả ra
    `db_session` y nguyên lúc `__enter__`.
    """
    from src.api import routes

    called: list[str] = []
    monkeypatch.setattr(
        routes, "ingest_file", lambda _db, path: called.append(str(path)) or 3
    )

    class _NonClosingSession:
        def __enter__(self):
            return db_session

        def __exit__(self, *exc_info):
            return False

    monkeypatch.setattr(routes, "SessionLocal", lambda: _NonClosingSession())
    return called


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Bộ đếm rate limit (task 18, `src/services/rate_limit.py`) sống ở biến
    MODULE-LEVEL, ngoài `db_session` — không tự dọn giữa các test.

    `autouse`: nếu không reset, các test gọi `/chat` / tải tệp / nạp tài liệu
    nhiều lần rải rác khắp file (không test nào tự nghĩ mình đang "dùng hết
    hạn mức") sẽ CỘNG DỒN vào cùng bucket IP mặc định của `httpx.ASGITransport`
    và bắt đầu ăn 429 một cách ngẫu nhiên tuỳ thứ tự chạy — sai hoàn toàn với
    ý định của các test đó.
    """
    from src.services import rate_limit

    rate_limit.reset_all()
    yield
