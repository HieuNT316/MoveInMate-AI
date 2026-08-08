"""SQLAlchemy models — bám sát docs/PROJECT_CHARTER.md mục 6.

Hai lựa chọn kỹ thuật cần biết trước khi sửa:

1. ENUM dùng `native_enum=False` → sinh ra VARCHAR + CHECK constraint thay vì
   type ENUM của Postgres. Lý do: thêm giá trị vào ENUM native phải ALTER TYPE,
   không rollback được trong transaction của Alembic. `apartment_type` và các
   giá trị tiện ích còn đang chờ dữ liệu thật (charter mục 7) nên phải đổi được rẻ.

2. `JSON().with_variant(JSONB, "postgresql")` → chạy JSONB trên Supabase,
   vẫn chạy được SQLite khi dev máy cá nhân chưa có DB.

APPLICATIONS chưa tạo — charter xếp Phase 2, không migrate ở GATE 2.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSONType = JSON().with_variant(JSONB, "postgresql")

ROLES = ("resident", "admin")
OWNERSHIP_TYPES = ("owner", "renter")
ITEM_TYPES = ("bql_actionable", "third_party_info")
ANSWER_SOURCES = ("faq", "rag", "no_context")


class Base(DeclarativeBase):
    pass


class User(Base):
    """Cư dân và tài khoản BQL. Tài khoản do BQL cấp, cư dân không tự đăng ký."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Trỏ sang auth.users của Supabase. KHÔNG khai FK ở tầng DB: bảng đó nằm
    # trong schema `auth` do Supabase quản lý, Alembic không nên đụng vào.
    # Nullable vì BQL có thể tạo hồ sơ cư dân trước khi gửi lời mời tạo tài khoản.
    auth_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True)

    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    apartment: Mapped[str] = mapped_column(String(50))
    building: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(
        SAEnum(*ROLES, name="user_role", native_enum=False), default="resident"
    )

    # --- Bốn field dưới đây là đầu vào của rule engine (src/services/checklist.py).
    # Đổi tên/kiểu ở đây là phá vỡ PROFILE_FIELDS bên đó.
    ownership_type: Mapped[str | None] = mapped_column(
        SAEnum(*OWNERSHIP_TYPES, name="ownership_type", native_enum=False)
    )
    apartment_type: Mapped[str | None] = mapped_column(String(50))
    has_car: Mapped[bool] = mapped_column(Boolean, default=False)
    amenity_packages: Mapped[list[str]] = mapped_column(JSONType, default=list)

    # Chỉ ghi ở lần hoàn thành onboarding ĐẦU TIÊN — metric "% cư dân xong
    # onboarding trong X ngày đầu" cần mốc đầu, không phải lần gần nhất.
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    completions: Mapped[list[ChecklistCompletion]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ChecklistItem(Base):
    """Bảng template dùng chung. KHÔNG chốt cứng cho từng cư dân — lọc trực tiếp."""

    __tablename__ = "checklist_items"

    checklist_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    item_type: Mapped[str] = mapped_column(
        SAEnum(*ITEM_TYPES, name="item_type", native_enum=False)
    )

    # `{}` = áp dụng mọi cư dân. Key phải nằm trong PROFILE_FIELDS của rule engine —
    # validate lúc seed (scripts/seed_data.py), DB không tự kiểm được điều này.
    conditions: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class ChecklistCompletion(Base):
    """Chỉ lưu mục ĐÃ xong. Không có dòng = chưa xong, không cần cột trạng thái."""

    __tablename__ = "checklist_completions"
    __table_args__ = (UniqueConstraint("user_id", "checklist_item_id", name="uq_completion"),)

    completion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    checklist_item_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_items.checklist_item_id", ondelete="CASCADE")
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="completions")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    chat_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)

    # Câu trả lời đến từ đâu. Khác với `source_type` của tài liệu
    # (bql_internal / public_regulation / unofficial_web) — đừng lẫn hai khái niệm.
    answer_source: Mapped[str] = mapped_column(
        SAEnum(*ANSWER_SOURCES, name="answer_source", native_enum=False)
    )

    # [{document_id, title, snippet}] — lấy từ node retrieve, KHÔNG để LLM sinh.
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    """Metadata tài liệu. Nội dung đã chunk + embed nằm ở Chroma, không ở đây."""

    __tablename__ = "documents"

    document_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(500))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Faq(Base):
    """Fallback chạy TRƯỚC RAG trong LangGraph. Code nhánh này hoãn sang W4."""

    __tablename__ = "faq"
    __table_args__ = (CheckConstraint("length(question) > 0", name="ck_faq_question_not_empty"),)

    faq_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
