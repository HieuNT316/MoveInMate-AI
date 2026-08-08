"""API routes.

Hiện gom trong một file vì mỗi endpoint chỉ vài dòng. Khi logic dày lên thì
tách thành package `src/api/routes/` như mô tả ở docs/architecture_diagram.md
mục 3.2.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, require_admin
from src.database import get_db
from src.models.schemas import (
    ChatHistoryEntry,
    ChatRequest,
    ChatResponse,
    ChecklistItemResponse,
    ChecklistResponse,
    CompletionRequest,
    CreateUserRequest,
    DashboardResponse,
    DemoAccount,
    LoginRequest,
    OnboardingRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from src.services import mock_chat, store
from src.services.checklist import generate_checklist, only_bql_scope, summarize_progress

router = APIRouter()


# --- Đăng nhập ----------------------------------------------------------


@router.post("/auth/login", response_model=ProfileResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Any:
    """⚠️ TẠM THỜI — tra người dùng theo email, KHÔNG kiểm mật khẩu.

    Đây không phải xác thực và không được để lên production. Nó tồn tại để
    demo chạy được nhiều persona trước khi dựng Supabase Auth.
    """
    user = store.get_user_by_email(db, payload.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email không có trong hệ thống. Tài khoản do Ban quản lý cấp.",
        )
    return user


def _describe(user: dict[str, Any]) -> str:
    """Mô tả hồ sơ bằng đúng các trường rule engine dùng để lọc."""
    if user["role"] == "admin":
        return "Ban quản lý · xem tiến độ toàn khu"
    if user["ownership_type"] is None:
        return "Chưa thiết lập hồ sơ · sẽ vào form onboarding"

    parts = ["Chủ hộ" if user["ownership_type"] == "owner" else "Người thuê"]
    if user["apartment_type"]:
        parts.append(user["apartment_type"].upper())
    parts.append("có ô tô" if user["has_car"] else "không xe")
    parts.append(
        ", ".join(user["amenity_packages"]) if user["amenity_packages"] else "không gói tiện ích"
    )
    return " · ".join(parts)


# Mỗi tuple: (nhãn, hàm lọc). Lấy người ĐẦU TIÊN khớp để danh sách ổn định
# giữa các lần gọi — dữ liệu seed tất định nên luôn ra cùng một bộ.
_DEMO_PATTERNS = [
    ("owner-full", lambda u: u["ownership_type"] == "owner" and u["has_car"] and len(u["amenity_packages"]) >= 2),
    ("owner-bare", lambda u: u["ownership_type"] == "owner" and not u["has_car"] and not u["amenity_packages"]),
    ("renter-car", lambda u: u["ownership_type"] == "renter" and u["has_car"]),
    ("renter-bare", lambda u: u["ownership_type"] == "renter" and not u["has_car"] and not u["amenity_packages"]),
    ("new", lambda u: u["ownership_type"] is None),
]


@router.get("/auth/demo-accounts", response_model=list[DemoAccount])
async def demo_accounts(db: Session = Depends(get_db)) -> Any:
    """⚠️ TẠM THỜI — các persona tương phản để demo, xoá cùng lúc với /auth/login.

    Chọn theo hồ sơ chứ không hardcode id: seed lại dữ liệu vẫn ra danh sách
    hợp lệ. `checklist_total` tính bằng chính rule engine nên con số khác nhau
    giữa các persona là bằng chứng cá nhân hóa đang chạy.
    """
    items = store.list_checklist_items(db)
    residents = store.list_residents(db)

    picked: list[dict[str, Any]] = []
    for _, predicate in _DEMO_PATTERNS:
        match = next((u for u in residents if predicate(u) and u not in picked), None)
        if match:
            picked.append(match)

    admin = store.get_admin(db)
    accounts = ([admin] if admin else []) + picked

    return [
        DemoAccount(
            user_id=u["user_id"],
            full_name=u["full_name"],
            email=u["email"],
            role=u["role"],
            summary=_describe(u),
            checklist_total=(
                0 if u["role"] == "admin" else len(generate_checklist(u, items))
            ),
        )
        for u in accounts
    ]


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
    db: Session = Depends(get_db),
) -> Any:
    """US-02 — lưu hồ sơ. Checklist không sinh ở đây mà lọc trực tiếp khi xem."""
    return store.save_onboarding(db, user["user_id"], payload.model_dump())


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """US-06 — sửa hồ sơ. Chỉ gửi field muốn đổi; checklist tự cập nhật theo."""
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần ít nhất một trường để cập nhật",
        )
    return store.update_profile(db, user["user_id"], changes)


def _build_checklist(db: Session, user: dict[str, Any]) -> ChecklistResponse:
    """Lọc checklist theo hồ sơ và tổng hợp tiến độ cho hai đối tượng."""
    matched = generate_checklist(user, store.list_checklist_items(db))
    done = store.get_completions(db, user["user_id"])
    done_ids = set(done)

    items = [
        ChecklistItemResponse(
            **{k: v for k, v in item.items() if k != "conditions"},
            completed=item["id"] in done_ids,
            completed_at=done.get(item["id"]),
        )
        for item in matched
    ]
    return ChecklistResponse(
        items=items,
        overall=summarize_progress(matched, done_ids),
        bql_scope=summarize_progress(only_bql_scope(matched), done_ids),
        onboarding_completed=user["onboarding_completed_at"] is not None,
    )


@router.get("/checklist", response_model=ChecklistResponse)
async def get_checklist(
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChecklistResponse:
    """US-04 — checklist cá nhân hóa, tính lại mỗi lần gọi."""
    return _build_checklist(db, user)


@router.patch("/checklist/{item_id}", response_model=ChecklistResponse)
async def set_checklist_item(
    item_id: int,
    payload: CompletionRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChecklistResponse:
    """US-04 — đánh dấu hoàn thành.

    Trả về **toàn bộ checklist đã cập nhật** thay vì riêng mục vừa sửa, để
    frontend cập nhật cả thanh tiến độ trong một lượt gọi.
    """
    known = {item["id"] for item in store.list_checklist_items(db)}
    if item_id not in known:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục này"
        )
    store.set_completion(db, user["user_id"], item_id, payload.completed)
    return _build_checklist(db, user)


# --- Hỏi đáp ------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """US-05 — hỏi đáp thủ tục. Câu trả lời luôn kèm nguồn, hoặc từ chối."""
    result = mock_chat.answer_question(payload.message)
    store.add_chat(db, user["user_id"], {"question": payload.message, **result})
    return result


@router.get("/chat/history", response_model=list[ChatHistoryEntry])
async def chat_history(
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """US-07 — lịch sử hội thoại của chính người dùng."""
    return store.list_chat(db, user["user_id"])


# --- Ban quản lý --------------------------------------------------------


@router.post(
    "/admin/users", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_resident(
    payload: CreateUserRequest,
    _admin: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """US-00 — BQL tạo tài khoản cư dân. Cư dân không tự đăng ký được."""
    return store.create_user(db, payload.model_dump())


@router.get("/admin/dashboard", response_model=DashboardResponse)
async def dashboard(
    _admin: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """Tiến độ onboarding của toàn bộ cư dân, để BQL chủ động hỗ trợ."""
    items = store.list_checklist_items(db)
    residents = []
    for resident in store.list_residents(db):
        matched = only_bql_scope(generate_checklist(resident, items))
        done_ids = set(store.get_completions(db, resident["user_id"]))
        residents.append(
            {
                "user_id": resident["user_id"],
                "full_name": resident["full_name"],
                "apartment": resident["apartment"],
                "ownership_type": resident["ownership_type"],
                "onboarded": resident["onboarding_completed_at"] is not None,
                "bql_scope": summarize_progress(matched, done_ids),
            }
        )
    return DashboardResponse(residents=residents, total_residents=len(residents))
