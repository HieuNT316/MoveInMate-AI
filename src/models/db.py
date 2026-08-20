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
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Mã giấy tờ; nhãn hiển thị nằm ở đó luôn, không ở DB — sửa một chữ hiển thị
# không nên phải viết migration.
from src.services.documents import DOCUMENT_CODES

JSONType = JSON().with_variant(JSONB, "postgresql")

ROLES = ("resident", "admin")
ACCOUNT_STATUSES = ("active", "locked")
EMBED_STATUSES = ("pending", "processing", "ready", "failed")
OWNERSHIP_TYPES = ("owner", "renter")
ITEM_TYPES = ("bql_actionable", "third_party_info")
ANSWER_SOURCES = ("faq", "rag", "no_context")

# US-13 — vòng đời hồ sơ, bám đúng quy trình mô tả trong
# data/kb/bql/bql-co-cau-va-quy-trinh.md. Không tự đặt thêm trạng thái: cư dân
# đối chiếu được với thứ BQL nói ngoài đời thì mới có ích.
APPLICATION_STATUSES = (
    "received",    # Đã tiếp nhận
    "processing",  # Đang xử lý
    "needs_info",  # Cần bổ sung
    "approved",    # Đã duyệt
    "delivered",   # Đã trả kết quả
    "rejected",    # Từ chối
)

# Hồ sơ đã kết thúc vòng đời — nộp lại cùng thủ tục là hợp lệ. Các trạng thái
# còn lại tính là "đang mở", chặn nộp trùng.
CLOSED_STATUSES = ("delivered", "rejected")

# Hai loại hồ sơ KHÁC BẢN CHẤT, không được gộp:
#
#   bql_processing — BQL thật sự tiếp nhận và xử lý (thẻ xe, thẻ cư dân). Có bộ
#                    phận phụ trách, chạy đủ vòng đời trạng thái.
#   self_declared  — thủ tục làm ở cơ quan khác (tạm trú, cập nhật cư trú). BQL
#                    KHÔNG xử lý, chỉ ghi nhận ảnh minh chứng cư dân tự nộp.
#
# Gộp chung sẽ khiến giao diện nói "Ban quản lý đang xử lý hồ sơ tạm trú của
# bạn" — sai sự thật, và phá nguyên tắc sản phẩm không mạo nhận quy trình của
# cơ quan khác (PROJECT_CHARTER.md mục 7).
APPLICATION_KINDS = ("bql_processing", "self_declared")


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

    # Khoá do BQL đặt. Kiểm trong `get_current_user` nên áp cho MỌI endpoint,
    # không phải nhớ gắn từng chỗ.
    account_status: Mapped[str] = mapped_column(
        SAEnum(*ACCOUNT_STATUSES, name="account_status", native_enum=False),
        default="active",
        server_default="active",
        nullable=False,
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

    # US-13 — định tuyến hồ sơ. Chép TẤT ĐỊNH từ bảng định tuyến trong
    # data/kb/bql/bql-co-cau-va-quy-trinh.md, không hỏi LLM: thủ tục hành chính
    # cần đúng tuyệt đối và giải thích được, cùng lý do đã áp cho rule engine.
    #
    # NULL với mục `third_party_info`: tạm trú và cập nhật cư trú do công an
    # phường xử lý, BQL không tiếp nhận nên không có bộ phận nào để định tuyến.
    # `seed_data` kiểm bất biến này lúc nạp.
    handling_department: Mapped[str | None] = mapped_column(String(100))
    submission_location: Mapped[str | None] = mapped_column(String(255))
    processing_time: Mapped[str | None] = mapped_column(String(100))

    # US-13/D1 — mã giấy tờ thủ tục này yêu cầu, chép từ mục "Giấy tờ cần mang"
    # trong data/kb/bql/. Rỗng = không đòi giấy tờ nào. `seed_data` kiểm mã hợp
    # lệ lúc nạp.
    required_documents: Mapped[list[str]] = mapped_column(JSONType, default=list)

    # AI Form Generation (task 3) — schema for dynamic form, NULL = no form.
    form_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONType, default=None)


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


class Application(Base):
    """US-13 — hồ sơ cư dân nộp trực tuyến cho một thủ tục trong checklist.

    KHÔNG trùng khái niệm với `ChecklistCompletion`: nộp hồ sơ là gửi yêu cầu
    đi, tick checklist là cư dân tự xác nhận đã xong. Một người có thể nộp hồ sơ
    rồi vẫn chưa tick, hoặc tick mà chưa từng nộp (làm trực tiếp ở quầy).

    Không lưu bộ phận xử lý ở đây — tra thẳng từ `checklist_items` mỗi lần đọc.
    Bảng định tuyến đổi thì mọi hồ sơ hiện đúng ngay, không phải đi vá dữ liệu cũ.
    """

    __tablename__ = "applications"
    __table_args__ = (
        # Chốt chặn ở tầng DB cho quy tắc "một hồ sơ đang mở cho mỗi mục checklist"
        # mà tầng ứng dụng đã kiểm (get_open_application). Đọc-rồi-ghi ở tầng ứng
        # dụng không chặn được hai request đến cùng lúc; index bộ phận này thì có.
        # Chỉ áp cho hồ sơ CHƯA đóng — CLOSED_STATUSES đóng vòng đời, nộp lại là hợp lệ.
        Index(
            "uq_open_application_per_item",
            "user_id",
            "checklist_item_id",
            unique=True,
            postgresql_where=text("status NOT IN ('delivered', 'rejected')"),
            sqlite_where=text("status NOT IN ('delivered', 'rejected')"),
        ),
    )

    application_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    checklist_item_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_items.checklist_item_id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(
        SAEnum(*APPLICATION_STATUSES, name="application_status", native_enum=False),
        default="received",
        index=True,
    )

    # Suy ra từ `item_type` của mục checklist lúc nộp, không do client khai.
    kind: Mapped[str] = mapped_column(
        SAEnum(*APPLICATION_KINDS, name="application_kind", native_enum=False),
        default="bql_processing",
    )

    # Cư dân ghi khi nộp (vd. biển số xe); BQL ghi khi đổi trạng thái (vd. thiếu
    # giấy tờ gì). Hai chiều tách riêng để cư dân không sửa được lời của BQL.
    note: Mapped[str | None] = mapped_column(Text)
    bql_note: Mapped[str | None] = mapped_column(Text)
    form_data: Mapped[dict | None] = mapped_column(JSONType, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship()
    item: Mapped[ChecklistItem] = relationship()
    attachments: Mapped[list[ApplicationAttachment]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class ApplicationAttachment(Base):
    """Ảnh minh chứng cư dân tải lên cho một hồ sơ (US-13).

    Chỉ lưu METADATA ở đây; nội dung tệp nằm trong bucket private của Supabase
    Storage (`src/services/storage.py`). Không nhét binary vào DB: mọi truy vấn
    hồ sơ sẽ phải kéo theo ảnh dù không cần.

    `storage_path` do backend sinh bằng UUID, không dùng tên file client gửi —
    tên gốc chỉ giữ ở `filename` để hiển thị.
    """

    __tablename__ = "application_attachments"

    attachment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.application_id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))

    # NULL = CHƯA PHÂN LOẠI, khác hẳn `khac` (cư dân đã gán, chỉ là không thuộc
    # loại nào). Gộp hai thứ này lại là mất khả năng phân biệt "chưa ai gán"
    # với "đã xem và xếp vào loại khác" — mà đó chính là thứ quyết định hệ
    # thống có được phép kết luận "thiếu giấy tờ" hay không.
    document_type: Mapped[str | None] = mapped_column(
        SAEnum(*DOCUMENT_CODES, name="document_type", native_enum=False)
    )
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(512))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    application: Mapped[Application] = relationship(back_populates="attachments")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    chat_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))

    # Gom các lượt hỏi đáp thuộc cùng một cuộc hội thoại multi-turn — để "bấm
    # vào hỏi tiếp" biết lấy đúng lịch sử nào làm ngữ cảnh viết lại câu hỏi
    # (`rewrite_query`). Mỗi cuộc hội thoại mới sinh một UUID mới ở backend;
    # tiếp tục hội thoại cũ thì client gửi lại đúng id này.
    conversation_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)

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
    # Embed mất từ nửa phút tới vài phút (15 chunk mỗi lượt, nghỉ 12 giây) nên
    # chạy nền. Container chết giữa chừng thì bản ghi kẹt ở `processing` và BQL
    # bấm nạp lại — đủ cho phạm vi này, không dựng hàng đợi.
    embed_status: Mapped[str] = mapped_column(
        SAEnum(*EMBED_STATUSES, name="embed_status", native_enum=False),
        default="ready",
        server_default="ready",
        nullable=False,
    )


class Faq(Base):
    """Fallback chạy TRƯỚC RAG trong LangGraph. Code nhánh này hoãn sang W4."""

    __tablename__ = "faq"
    __table_args__ = (CheckConstraint("length(question) > 0", name="ck_faq_question_not_empty"),)

    faq_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
