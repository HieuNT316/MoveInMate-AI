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

from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from src.models.db import (
    CLOSED_STATUSES,
    Application,
    ApplicationAttachment,
    ChatHistory,
    ChecklistCompletion,
    ChecklistItem,
    Document,
    User,
)
from src.models.schemas import FormSchemaPayload
from src.services.documents import describe, evaluate_documents
from src.services.pii import mask_answer, mask_question

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


def get_checklist_item(db: Session, checklist_item_id: int) -> dict[str, Any] | None:
    item = db.get(ChecklistItem, checklist_item_id)
    return _item_dict(item) if item else None


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
    """Ghi một lượt hỏi đáp — nơi DUY NHẤT insert vào `chat_history`.

    Che PII (V8, `src/services/pii.py`) ngay tại đây, trước insert: đảm bảo
    này phải đứng ở code, không phải ở prompt, và đứng ở điểm ghi DUY NHẤT
    này thì mọi lối gọi (hiện chỉ có `src/api/routes.py`) đều được bọc, không
    cần nhớ gọi mask ở từng call site.
    """
    db.add(
        ChatHistory(
            user_id=user_id,
            conversation_id=conversation_id,
            question=mask_question(payload["question"]),
            answer=mask_answer(payload["answer"]),
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
        "user_id": app.user_id,
        "checklist_item_id": app.checklist_item_id,
        "task_name": app.item.task_name,
        "status": app.status,
        "kind": app.kind,
        "handling_department": app.item.handling_department,
        "submission_location": app.item.submission_location,
        "processing_time": app.item.processing_time,
        "note": app.note,
        "bql_note": app.bql_note,
        "form_data": app.form_data or {},
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


class ValidationError(Exception):
    """Loi validate form_data cua AI Form Generation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


class DuplicateApplicationError(Exception):
    """`uq_open_application_per_item` (src/models/db.py) chặn insert.

    `get_open_application` là đọc-rồi-ghi: hai request đến cùng lúc đều có thể
    đọc "chưa có hồ sơ mở" trước khi request kia commit. Insert thua cuộc rơi
    vào đây thay vì để `IntegrityError` thô bay lên route thành 500 — người
    gọi (route) bắt exception này và trả đúng 409 như nhánh kiểm tuần tự.
    """


def validate_form_data(schema: FormSchemaPayload, form_data: dict) -> list[str]:
    """Tra ve danh sach loi. Empty = hop le."""
    import re

    errors = []
    for field in schema.fields:
        if field.required and field.key not in form_data:
            errors.append(f"Thiếu: {field.label}")
        elif field.key in form_data:
            value = str(form_data[field.key])
            if field.pattern and not re.match(field.pattern, value):
                errors.append(f"{field.label} sai định dạng")
    return errors


def get_form_schema(db: Session, item_id: int) -> FormSchemaPayload | None:
    item = db.get(ChecklistItem, item_id)
    if item is None or item.form_schema is None:
        return None
    return FormSchemaPayload.model_validate(item.form_schema)


def create_application(
    db: Session,
    user_id: int,
    checklist_item_id: int,
    kind: str,
    note: str | None = None,
    form_data: dict | None = None,
) -> dict[str, Any]:
    # Validate form_data neu co
    if form_data:
        schema = get_form_schema(db, checklist_item_id)
        if schema:
            errors = validate_form_data(schema, form_data)
            if errors:
                raise ValidationError(errors)
    app = Application(
        user_id=user_id,
        checklist_item_id=checklist_item_id,
        note=note,
        status="received",
        kind=kind,
        form_data=form_data or {},
    )
    db.add(app)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateApplicationError() from None
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


class VersionConflictError(Exception):
    """Hồ sơ đã bị sửa bởi người khác — client phải refresh."""


def update_application_status(
    db: Session,
    application_id: int,
    status: str,
    bql_note: str | None,
    form_data: dict[str, str] | None,
    expected_version: int | None = None,
) -> dict[str, Any] | None:
    """Cập nhật trạng thái hồ sơ với optimistic locking tuỳ chọn.

    Nếu `expected_version` được truyền, hàm sẽ kiểm tra version hiện tại
    và raise `VersionConflictError` nếu không khớp.
    """
    if expected_version is not None:
        # Optimistic locking: kiểm tra version trước, rồi mới UPDATE.
        # Tách làm hai query để đảm bảo tương thích SQLite (RETURNING + rowcount
        # không hoạt động đáng tin cậy trên SQLite).
        app = db.scalar(
            select(Application).where(Application.application_id == application_id)
        )
        if app is None:
            return None
        if app.version != expected_version:
            raise VersionConflictError(
                f"Application {application_id} was modified by another user. Please refresh."
            )

        app.status = status
        if bql_note is not None:
            app.bql_note = bql_note
        if form_data is not None:
            app.form_data = form_data
        app.version = (app.version or 1) + 1

        db.commit()
        db.refresh(app)
        return _application_dict(app)

    # Không có optimistic locking: dùng ORM như trước
    app = db.scalar(select(Application).where(Application.application_id == application_id))
    if app is None:
        return None

    app.status = status
    # Chỉ ghi đè khi BQL thực sự gửi ghi chú — đổi trạng thái mà không nói gì
    # thì giữ nguyên lời nhắn cũ, đừng xoá mất lý do "cần bổ sung" trước đó.
    if bql_note is not None:
        app.bql_note = bql_note
    # Chỉ ghi đè khi BQL thực sự gửi form_data — None = giữ nguyên, {} = xoá.
    if form_data is not None:
        app.form_data = form_data
    app.version = (app.version or 1) + 1

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


# --- BQL nạp tài liệu (US-08) --------------------------------------------


def _document_dict(doc: Document) -> dict[str, Any]:
    return {
        "document_id": doc.document_id,
        "title": doc.title,
        "file_path": doc.file_path,
        "embed_status": doc.embed_status,
        "uploaded_at": _as_utc(doc.uploaded_at),
    }


def create_document_record(
    db: Session, file_path: str, title: str, embed_status: str
) -> dict[str, Any]:
    doc = Document(file_path=file_path, title=title, embed_status=embed_status)
    db.add(doc)
    db.commit()
    return _document_dict(doc)


def set_embed_status(db: Session, document_id: int, embed_status: str) -> None:
    doc = db.get(Document, document_id)
    if doc is not None:
        doc.embed_status = embed_status
        db.commit()


def list_documents(db: Session) -> list[dict[str, Any]]:
    return [
        _document_dict(d)
        for d in db.scalars(select(Document).order_by(Document.document_id.desc()))
    ]


def get_document(db: Session, document_id: int) -> dict[str, Any] | None:
    """Get a single document by ID, or None if not found."""
    doc = db.get(Document, document_id)
    return _document_dict(doc) if doc else None


# --- Hỗ trợ (Tickets) ----------------------------------------------------


def create_ticket(
    db: Session,
    user_id: int,
    subject: str,
    initial_message: str | None = None,
) -> dict[str, Any]:
    """Create a new support ticket."""
    stmt = text("""
        INSERT INTO tickets (user_id, subject, status, priority)
        VALUES (:user_id, :subject, 'open', 'normal')
        RETURNING ticket_id, user_id, subject, status, priority, assigned_to, created_at
    """)
    result = db.execute(stmt, {"user_id": user_id, "subject": subject})
    db.commit()
    ticket = dict(result.one()._mapping)

    if initial_message:
        add_ticket_message(db, ticket["ticket_id"], user_id, "resident", initial_message)

    return ticket


def add_ticket_message(
    db: Session,
    ticket_id: int,
    sender_id: int,
    sender_type: str,
    message: str,
) -> dict[str, Any]:
    """Add message to ticket."""
    stmt = text("""
        INSERT INTO ticket_messages (ticket_id, sender_id, sender_type, message)
        VALUES (:ticket_id, :sender_id, :sender_type, :message)
        RETURNING message_id, ticket_id, sender_id, sender_type, message, created_at
    """)
    result = db.execute(stmt, {
        "ticket_id": ticket_id,
        "sender_id": sender_id,
        "sender_type": sender_type,
        "message": message,
    })
    db.commit()
    return dict(result.one()._mapping)


def get_user_tickets(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Get all tickets for a user."""
    stmt = text("""
        SELECT t.*,
               (SELECT message FROM ticket_messages tm WHERE tm.ticket_id = t.ticket_id ORDER BY created_at DESC LIMIT 1) as last_message
        FROM tickets t
        WHERE t.user_id = :user_id
        ORDER BY t.created_at DESC
    """)
    result = db.execute(stmt, {"user_id": user_id})
    return [dict(row._mapping) for row in result.fetchall()]


def get_ticket_with_messages(db: Session, ticket_id: int, user_id: int) -> dict[str, Any] | None:
    """Get ticket with all messages (for resident, only own tickets)."""
    stmt = text("""
        SELECT t.*, u.full_name as assigned_to_name
        FROM tickets t
        LEFT JOIN users u ON t.assigned_to = u.user_id
        WHERE t.ticket_id = :ticket_id AND t.user_id = :user_id
    """)
    result = db.execute(stmt, {"ticket_id": ticket_id, "user_id": user_id})
    row = result.fetchone()
    if not row:
        return None

    ticket = dict(row._mapping)

    msg_stmt = text("""
        SELECT tm.*, u.full_name as sender_name
        FROM ticket_messages tm
        JOIN users u ON tm.sender_id = u.user_id
        WHERE tm.ticket_id = :ticket_id
        ORDER BY tm.created_at ASC
    """)
    msg_result = db.execute(msg_stmt, {"ticket_id": ticket_id})
    ticket["messages"] = [dict(row._mapping) for row in msg_result.fetchall()]

    return ticket


def get_ticket_by_id(db: Session, ticket_id: int) -> dict[str, Any] | None:
    """Get ticket by ID (admin view, no user filter)."""
    stmt = text("""
        SELECT t.*, u.full_name as user_name, a.full_name as assigned_to_name
        FROM tickets t
        JOIN users u ON t.user_id = u.user_id
        LEFT JOIN users a ON t.assigned_to = a.user_id
        WHERE t.ticket_id = :ticket_id
    """)
    result = db.execute(stmt, {"ticket_id": ticket_id})
    row = result.fetchone()
    if not row:
        return None
    return dict(row._mapping)


def assign_ticket(db: Session, ticket_id: int, assigned_to: int) -> dict[str, Any] | None:
    """Assign ticket to a user."""
    stmt = text("""
        UPDATE tickets
        SET assigned_to = :assigned_to, status = 'in_progress', updated_at = NOW()
        WHERE ticket_id = :ticket_id
        RETURNING *
    """)
    result = db.execute(stmt, {"ticket_id": ticket_id, "assigned_to": assigned_to})
    db.commit()
    row = result.fetchone()
    return dict(row._mapping) if row else None


def resolve_ticket(db: Session, ticket_id: int) -> dict[str, Any] | None:
    """Mark ticket as resolved."""
    stmt = text("""
        UPDATE tickets
        SET status = 'resolved', resolved_at = NOW(), updated_at = NOW()
        WHERE ticket_id = :ticket_id
        RETURNING *
    """)
    result = db.execute(stmt, {"ticket_id": ticket_id})
    db.commit()
    row = result.fetchone()
    return dict(row._mapping) if row else None


def update_ticket_status(db: Session, ticket_id: int, status: str) -> dict[str, Any] | None:
    """Update ticket status."""
    stmt = text("""
        UPDATE tickets
        SET status = :status, updated_at = NOW()
        WHERE ticket_id = :ticket_id
        RETURNING *
    """)
    result = db.execute(stmt, {"ticket_id": ticket_id, "status": status})
    db.commit()
    row = result.fetchone()
    return dict(row._mapping) if row else None


def get_all_tickets(
    db: Session,
    status: str | None = None,
    assigned_to: int | None = None,
) -> list[dict[str, Any]]:
    """Get all tickets (for admin)."""
    query = """
        SELECT t.*, u.full_name as user_name, a.full_name as assigned_to_name
        FROM tickets t
        JOIN users u ON t.user_id = u.user_id
        LEFT JOIN users a ON t.assigned_to = a.user_id
        WHERE 1=1
    """
    params = {}
    if status:
        query += " AND t.status = :status"
        params["status"] = status
    if assigned_to:
        query += " AND t.assigned_to = :assigned_to"
        params["assigned_to"] = assigned_to
    query += " ORDER BY t.created_at DESC"

    result = db.execute(text(query), params)
    return [dict(row._mapping) for row in result.fetchall()]
