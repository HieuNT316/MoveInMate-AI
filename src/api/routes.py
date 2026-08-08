"""API routes — bản demo luồng.

Hiện gom trong một file vì mỗi endpoint chỉ vài dòng. Khi thay lưu trữ thật
và logic dày lên thì tách thành package `src/api/routes/` như mô tả ở
docs/architecture_diagram.md mục 3.2.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import get_current_user, require_admin
from src.models.schemas import (
    ChatHistoryEntry,
    ChatRequest,
    ChatResponse,
    ChecklistItemResponse,
    ChecklistResponse,
    CompletionRequest,
    CreateUserRequest,
    OnboardingRequest,
    ProfileResponse,
)
from src.services import mock_chat, mock_store
from src.services.checklist import generate_checklist, progress_percent

router = APIRouter()


# --- Cư dân -------------------------------------------------------------


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user: dict[str, Any] = Depends(get_current_user)) -> Any:
    """US-06 — hồ sơ cư dân.

    `onboarding_completed_at = null` là tín hiệu để frontend chuyển hướng
    sang trang onboarding.
    """
    return user


@router.post("/onboarding", response_model=ProfileResponse)
async def submit_onboarding(
    payload: OnboardingRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> Any:
    """US-02 — lưu hồ sơ. Checklist không sinh ở đây mà lọc trực tiếp khi xem."""
    return mock_store.save_onboarding(user["user_id"], payload.model_dump())


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    payload: OnboardingRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> Any:
    """US-06 — sửa hồ sơ; checklist tự cập nhật theo vì được lọc trực tiếp."""
    return mock_store.update_profile(user["user_id"], payload.model_dump())


@router.get("/checklist", response_model=ChecklistResponse)
async def get_checklist(
    user: dict[str, Any] = Depends(get_current_user),
) -> ChecklistResponse:
    """US-04 — checklist cá nhân hóa, tính lại mỗi lần gọi."""
    matched = generate_checklist(user, mock_store.list_checklist_items())
    done = mock_store.get_completions(user["user_id"])

    items = [
        ChecklistItemResponse(
            **{k: v for k, v in item.items() if k != "conditions"},
            completed=item["id"] in done,
            completed_at=done.get(item["id"]),
        )
        for item in matched
    ]
    completed_count = sum(1 for item in items if item.completed)
    return ChecklistResponse(
        items=items,
        total=len(items),
        completed_count=completed_count,
        progress_percent=progress_percent(len(items), completed_count),
    )


@router.patch("/checklist/{item_id}", response_model=ChecklistResponse)
async def set_checklist_item(
    item_id: int,
    payload: CompletionRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ChecklistResponse:
    """US-04 — đánh dấu hoàn thành, trả về checklist đã cập nhật."""
    known = {item["id"] for item in mock_store.list_checklist_items()}
    if item_id not in known:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục này"
        )
    mock_store.set_completion(user["user_id"], item_id, payload.completed)
    return await get_checklist(user)


# --- Hỏi đáp ------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> Any:
    """US-05 — hỏi đáp thủ tục. Câu trả lời luôn kèm nguồn, hoặc từ chối."""
    result = mock_chat.answer_question(payload.message)
    mock_store.add_chat(user["user_id"], {"question": payload.message, **result})
    return result


@router.get("/chat/history", response_model=list[ChatHistoryEntry])
async def chat_history(user: dict[str, Any] = Depends(get_current_user)) -> Any:
    """US-07 — lịch sử hội thoại của chính người dùng."""
    return mock_store.list_chat(user["user_id"])


# --- Ban quản lý --------------------------------------------------------


@router.post(
    "/admin/users", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_resident(
    payload: CreateUserRequest,
    _admin: dict[str, Any] = Depends(require_admin),
) -> Any:
    """US-00 — BQL tạo tài khoản cư dân. Cư dân không tự đăng ký được."""
    return mock_store.create_user(payload.model_dump())


@router.get("/admin/dashboard")
async def dashboard(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    """Tiến độ onboarding của toàn bộ cư dân, để BQL chủ động hỗ trợ."""
    items = mock_store.list_checklist_items()
    residents = []
    for resident in mock_store.list_users():
        matched = generate_checklist(resident, items)
        done = mock_store.get_completions(resident["user_id"])
        completed = sum(1 for item in matched if item["id"] in done)
        residents.append(
            {
                "user_id": resident["user_id"],
                "full_name": resident["full_name"],
                "apartment": resident["apartment"],
                "ownership_type": resident["ownership_type"],
                "onboarded": resident["onboarding_completed_at"] is not None,
                "total": len(matched),
                "completed": completed,
                "progress_percent": progress_percent(len(matched), completed),
            }
        )
    return {"residents": residents, "total_residents": len(residents)}
