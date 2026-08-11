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

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.models.db import ChatHistory, ChecklistCompletion, ChecklistItem, User

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
    }


# --- Người dùng ---------------------------------------------------------


def get_user(db: Session, user_id: int) -> dict[str, Any] | None:
    user = db.get(User, user_id)
    return _user_dict(user) if user else None


def get_user_by_email(db: Session, email: str) -> dict[str, Any] | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
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


def add_chat(db: Session, user_id: int, payload: dict[str, Any]) -> None:
    db.add(
        ChatHistory(
            user_id=user_id,
            question=payload["question"],
            answer=payload["answer"],
            answer_source=payload["answer_source"],
            sources=payload.get("sources") or [],
        )
    )
    db.commit()


def list_chat(db: Session, user_id: int) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(ChatHistory)
        .where(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.chat_id)
    )
    return [
        {
            "id": r.chat_id,
            "question": r.question,
            "answer": r.answer,
            "answer_source": r.answer_source,
            "sources": r.sources or [],
            "created_at": _as_utc(r.created_at),
        }
        for r in rows
    ]
