"""Truy vấn dữ liệu cho API.

Trả về dict thay vì ORM object để rule engine (`src/services/checklist.py`)
không phải biết gì về SQLAlchemy: nó vẫn là hàm thuần trên dict, test được
mà không cần DB.

Hàm nào cũng nhận `db: Session` ở tham số đầu — không giữ session toàn cục,
FastAPI mở và đóng mỗi request qua `get_db`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from src.models.db import (
    CLOSED_STATUSES,
    Application,
    ApplicationAttachment,
    ChatHistory,
    ChecklistCompletion,
    ChecklistItem,
    User,
)
from src.services.documents import describe, evaluate_documents

PROFILE_KEYS = ("ownership_type", "apartment_type", "has_car", "amenity_packages")


def _as_utc(value: datetime | None) -> datetime | None:
    """Gắn lại UTC cho datetime đọc từ DB.

    SQLite không lưu timezone nên giá trị đọc lên là naive, trong khi giá trị
    vừa ghi trong cùng request vẫn còn tz-aware. Không chuẩn hóa thì cùng một
    mốc thời gian lúc serialize ra "…Z" lúc không, và client sẽ hiểu chuỗi
    naive là giờ địa phương. Postgres không dính, nhưng nhánh dev thì có.
    """
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def _user_dict(user: User) -> dict[str, Any]:
    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "email": user.email,
        "apartment": user.apartment,
        "building": user.building,
        "role": user.role,
        "account_status": user.account_status,
        "auth_user_id": user.auth_user_id,
        "ownership_type": user.ownership_type,
        "apartment_type": user.apartment_type,
        "has_car": user.has_car,
        "amenity_packages": user.amenity_packages or [],
        "onboarding_completed_at": _as_utc(user.onboarding_completed_at),
    }


def _item_dict(item: ChecklistItem) -> dict[str, Any]:
    # Rule engine và API dùng khoá `id`; DB dùng `checklist_item_id`.
    return {
        "id": item.checklist_item_id,
        "task_name": item.task_name,
        "description": item.description or "",
        "category": item.category or "",
        "conditions": item.conditions or {},
        "item_type": item.item_type,
        "order_index": item.order_index,
        # US-13 — None với thủ tục ngoài phạm vi BQL.
        "handling_department": item.handling_department,
        "submission_location": item.submission_location,
        "processing_time": item.processing_time,
        "required_documents": describe(item.required_documents),
    }


# --- Người dùng ---------------------------------------------------------


def get_user(db: Session, user_id: int) -> dict[str, Any] | None:
    user = db.get(User, user_id)
    return _user_dict(user) if user else None


def get_user_by_auth_id(db: Session, auth_user_id: uuid.UUID) -> dict[str, Any] | None:
    """Tra hồ sơ cư dân từ `sub` của JWT Supabase (US-01)."""
    user = db.scalar(select(User).where(User.auth_user_id == auth_user_id))
    return _user_dict(user) if user else None


def link_auth_user(db: Session, user_id: int, auth_user_id: uuid.UUID) -> None:
    """Gắn tài khoản Supabase Auth vào hồ sơ cư dân đã có."""
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"Không có người dùng {user_id}")
    user.auth_user_id = auth_user_id
    db.commit()


def get_admin(db: Session) -> dict[str, Any] | None:
    """Tài khoản BQL đầu tiên — dùng cho danh sách demo, không dùng cho phân quyền."""
    user = db.scalar(select(User).where(User.role == "admin").order_by(User.user_id))
    return _user_dict(user) if user else None


def list_residents(db: Session) -> list[dict[str, Any]]:
    users = db.scalars(select(User).where(User.role == "resident").order_by(User.user_id))
    return [_user_dict(u) for u in users]


def create_user(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    user = User(role="resident", has_car=False, amenity_packages=[], **payload)
    db.add(user)
    db.commit()
    return _user_dict(user)


def save_onboarding(db: Session, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"Không có người dùng {user_id}")

    for key in PROFILE_KEYS:
        setattr(user, key, payload[key])

    # Chỉ ghi ở lần đầu — nộp lại form không được đẩy mốc thời gian đi.
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.now(UTC)

    db.commit()
    return _user_dict(user)


def set_account_status(db: Session, user_id: int, account_status: str) -> dict[str, Any]:
    user = db.get(User, user_id)
    user.account_status = account_status
    db.commit()
    return _user_dict(user)


def update_profile(db: Session, user_id: int, changes: dict[str, Any]) -> dict[str, Any]:
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"Không có người dùng {user_id}")

    for key, value in changes.items():
        setattr(user, key, value)

    db.commit()
    return _user_dict(user)


# --- Checklist ----------------------------------------------------------


def list_checklist_items(db: Session) -> list[dict[str, Any]]:
    items = db.scalars(select(ChecklistItem).order_by(ChecklistItem.order_index))
    return [_item_dict(i) for i in items]


def get_completions(db: Session, user_id: int) -> dict[int, datetime]:
    rows = db.scalars(
        select(ChecklistCompletion).where(ChecklistCompletion.user_id == user_id)
    )
    return {r.checklist_item_id: _as_utc(r.completed_at) for r in rows}


def set_completion(db: Session, user_id: int, item_id: int, completed: bool) -> None:
    """Có dòng = đã xong, xoá dòng = chưa xong. Không có cột trạng thái."""
    existing = db.scalar(
        select(ChecklistCompletion).where(
            ChecklistCompletion.user_id == user_id,
            ChecklistCompletion.checklist_item_id == item_id,
        )
    )
    if completed and existing is None:
        db.add(ChecklistCompletion(user_id=user_id, checklist_item_id=item_id))
    elif not completed and existing is not None:
        db.execute(
            delete(ChecklistCompletion).where(
                ChecklistCompletion.completion_id == existing.completion_id
            )
        )
    db.commit()


# --- Hội thoại ----------------------------------------------------------


def add_chat(
    db: Session, user_id: int, conversation_id: uuid.UUID, payload: dict[str, Any]
) -> None:
    db.add(
        ChatHistory(
            user_id=user_id,
            conversation_id=conversation_id,
            question=payload["question"],
            answer=payload["answer"],
            answer_source=payload["answer_source"],
            sources=payload.get("sources") or [],
        )
    )
    db.commit()


def _chat_entry(row: ChatHistory) -> dict[str, Any]:
    return {
        "id": row.chat_id,
        "question": row.question,
        "answer": row.answer,
        "answer_source": row.answer_source,
        "sources": row.sources or [],
        "created_at": _as_utc(row.created_at),
    }


def get_conversation_messages(
    db: Session, user_id: int, conversation_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Toàn bộ lượt hỏi đáp của MỘT hội thoại, theo thứ tự thời gian tăng dần.

    Lọc theo CẢ `user_id` lẫn `conversation_id` — không tin riêng
    `conversation_id`: chặn user A xem/tiếp tục được hội thoại của user B dù
    đoán đúng UUID. Rỗng nghĩa là hội thoại không tồn tại HOẶC không thuộc về
    người này — route không phân biệt hai trường hợp đó khi trả lỗi, tránh lộ
    thông tin "UUID này có tồn tại" cho người không sở hữu nó.
    """
    rows = db.scalars(
        select(ChatHistory)
        .where(
            ChatHistory.user_id == user_id,
            ChatHistory.conversation_id == conversation_id,
        )
        .order_by(ChatHistory.chat_id)
    )
    return [_chat_entry(r) for r in rows]


def list_conversations(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Nhóm CHAT_HISTORY theo `conversation_id`, mới nhất trước — danh sách
    hội thoại đã lưu để bấm vào xem lại/hỏi tiếp (US-07).

    Gom ở Python thay vì SQL GROUP BY: quy mô dữ liệu một cư dân nhỏ (vài
    chục hội thoại đã là nhiều), và tránh cú pháp aggregate lệch nhau giữa
    SQLite (dev) và Postgres (production).
    """
    rows = db.scalars(
        select(ChatHistory).where(ChatHistory.user_id == user_id).order_by(ChatHistory.chat_id)
    )
    grouped: dict[uuid.UUID, list[ChatHistory]] = {}
    for row in rows:
        grouped.setdefault(row.conversation_id, []).append(row)

    conversations = [
        {
            "conversation_id": conv_id,
            "preview": entries[0].question,
            "message_count": len(entries),
            "last_message_at": _as_utc(entries[-1].created_at),
        }
        for conv_id, entries in grouped.items()
    ]
    conversations.sort(key=lambda c: c["last_message_at"], reverse=True)
    return conversations


# --- Hồ sơ nộp trực tuyến (US-13) ---------------------------------------


def _application_dict(app: Application) -> dict[str, Any]:
    """Hồ sơ kèm thông tin định tuyến tra THẲNG từ checklist item.

    Không sao chép bộ phận/nơi nộp vào bảng `applications`: bảng định tuyến đổi
    thì mọi hồ sơ hiện đúng ngay, không phải đi vá dữ liệu cũ.
    """
    return {
        "application_id": app.application_id,
        "checklist_item_id": app.checklist_item_id,
        "task_name": app.item.task_name,
        "status": app.status,
        "kind": app.kind,
        "handling_department": app.item.handling_department,
        "submission_location": app.item.submission_location,
        "processing_time": app.item.processing_time,
        "note": app.note,
        "bql_note": app.bql_note,
        "attachments": [_attachment_dict(a) for a in app.attachments],
        **evaluate_documents(
            app.item.required_documents, [a.document_type for a in app.attachments]
        ),
        "created_at": _as_utc(app.created_at),
        "updated_at": _as_utc(app.updated_at),
    }


def _attachment_dict(att: ApplicationAttachment) -> dict[str, Any]:
    """Metadata tệp. `url` LUÔN None ở đây — ký theo yêu cầu (18/08).

    Trước đó mỗi tệp được ký ngay lúc đọc hồ sơ: một `httpx.post` ĐỒNG BỘ tới
    Supabase, bên trong route `async`, một lần cho mỗi tệp. Vừa tuần tự vừa
    chặn event loop nên mọi request của mọi người khác đều phải đợi.

    Giữ lại trường thay vì xoá hẳn để giao diện chưa kịp đổi không vỡ vì thiếu
    khoá — ảnh không hiện thì tốt hơn trang trắng.
    """
    return {
        "attachment_id": att.attachment_id,
        "filename": att.filename,
        "document_type": att.document_type,
        "content_type": att.content_type,
        "size_bytes": att.size_bytes,
        "url": None,
        "uploaded_at": _as_utc(att.uploaded_at),
    }


def get_open_application(db: Session, user_id: int, item_id: int) -> dict[str, Any] | None:
    """Hồ sơ CHƯA kết thúc của người này cho đúng thủ tục đó, nếu có.

    Dùng để chặn nộp trùng: đã trả kết quả hoặc bị từ chối thì nộp lại là hợp
    lệ, còn đang chờ xử lý mà nộp tiếp chỉ làm BQL nhận hai hồ sơ giống nhau.
    """
    app = db.scalar(
        select(Application).where(
            Application.user_id == user_id,
            Application.checklist_item_id == item_id,
            Application.status.not_in(CLOSED_STATUSES),
        )
    )
    return _application_dict(app) if app else None


def create_application(
    db: Session, user_id: int, item_id: int, note: str | None, kind: str
) -> dict[str, Any]:
    app = Application(
        user_id=user_id,
        checklist_item_id=item_id,
        note=note,
        status="received",
        kind=kind,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _application_dict(app)


def get_application(db: Session, application_id: int) -> Application | None:
    """Trả ORM object — người gọi cần kiểm quyền sở hữu trước khi dùng."""
    return db.scalar(select(Application).where(Application.application_id == application_id))


def get_attachment(
    db: Session, application_id: int, attachment_id: int
) -> ApplicationAttachment | None:
    """Tệp đính kèm, tra theo CẢ HAI khoá.

    Thiếu điều kiện `application_id` thì đoán được id tệp là đọc được ảnh giấy
    tờ của người khác — quyền phải kiểm trên cặp, không phải trên một id.
    """
    return db.scalar(
        select(ApplicationAttachment).where(
            ApplicationAttachment.attachment_id == attachment_id,
            ApplicationAttachment.application_id == application_id,
        )
    )


def add_attachment(
    db: Session,
    application_id: int,
    filename: str,
    content_type: str,
    size_bytes: int,
    storage_path: str,
    document_type: str | None = None,
) -> dict[str, Any]:
    att = ApplicationAttachment(
        application_id=application_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_path=storage_path,
        document_type=document_type,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return _attachment_dict(att)


def count_attachments(db: Session, application_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ApplicationAttachment)
            .where(ApplicationAttachment.application_id == application_id)
        )
        or 0
    )


def list_applications(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Hồ sơ của chính một cư dân, mới nhất trước."""
    apps = db.scalars(
        select(Application)
        .where(Application.user_id == user_id)
        .order_by(Application.application_id.desc())
    )
    return [_application_dict(a) for a in apps]


def list_all_applications(
    db: Session, status: str | None = None, department: str | None = None
) -> list[dict[str, Any]]:
    """Toàn bộ hồ sơ cho BQL, kèm thông tin cư dân để biết gọi ai.

    Lọc theo bộ phận chạy trên `checklist_items` chứ không trên `applications`
    — định tuyến là thuộc tính của THỦ TỤC, không phải của từng hồ sơ.
    """
    # `join` chỉ để LỌC theo bộ phận; muốn đọc `a.user`/`a.item` mà không bắn
    # thêm một truy vấn cho mỗi dòng thì phải nạp sẵn. Không có hai dòng này,
    # 10 hồ sơ tốn 12 truy vấn — với 40 cư dân là hàng trăm.
    query = (
        select(Application)
        .join(Application.item)
        .options(
            selectinload(Application.user),
            selectinload(Application.item),
            selectinload(Application.attachments),
        )
        .order_by(Application.application_id.desc())
    )
    if status:
        query = query.where(Application.status == status)
    if department:
        query = query.where(ChecklistItem.handling_department == department)

    return [
        {
            **_application_dict(a),
            "user_id": a.user_id,
            "full_name": a.user.full_name,
            "apartment": a.user.apartment,
        }
        for a in db.scalars(query)
    ]


def update_application_status(
    db: Session, application_id: int, status: str, bql_note: str | None
) -> dict[str, Any] | None:
    app = db.scalar(select(Application).where(Application.application_id == application_id))
    if app is None:
        return None

    app.status = status
    # Chỉ ghi đè khi BQL thực sự gửi ghi chú — đổi trạng thái mà không nói gì
    # thì giữ nguyên lời nhắn cũ, đừng xoá mất lý do "cần bổ sung" trước đó.
    if bql_note is not None:
        app.bql_note = bql_note

    db.commit()
    db.refresh(app)
    return _application_dict(app)


def set_attachment_type(
    db: Session, application_id: int, attachment_id: int, document_type: str | None
) -> dict[str, Any] | None:
    """Gán lại loại cho một tệp đã tải lên.

    Cần thiết chứ không phải tiện nghi: gán nhầm loại (hoặc chưa gán) thì hồ sơ
    kẹt ở trạng thái "thiếu giấy tờ đã nộp rồi" — Ban quản lý nhìn thấy tệp trên
    màn hình mà hệ thống vẫn kêu thiếu, và không ai sửa được. Đây cũng là đường
    dọn cho các tệp tải lên trước khi có `document_type`.
    """
    att = db.scalar(
        select(ApplicationAttachment).where(
            ApplicationAttachment.attachment_id == attachment_id,
            ApplicationAttachment.application_id == application_id,
        )
    )
    if att is None:
        return None

    att.document_type = document_type
    db.commit()
    db.refresh(att)
    return _attachment_dict(att)
