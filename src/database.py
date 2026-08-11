"""Engine và session SQLAlchemy.

`DATABASE_URL` trỏ Supabase Postgres khi chạy thật, mặc định SQLite để dev
máy cá nhân chạy được trước khi có project Supabase.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings

_settings = get_settings()

# check_same_thread chỉ áp dụng cho SQLite; Postgres không nhận tham số này.
_connect_args = (
    {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(_settings.database_url, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency cho FastAPI — mở session mỗi request, đóng khi xong."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
