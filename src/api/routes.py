"""API routes.

Hiện gom trong một file vì mỗi endpoint chỉ vài dòng. Khi logic dày lên thì
tách thành package `src/api/routes/` như mô tả ở docs/architecture_diagram.md
mục 3.2.
"""

import re
import unicodedata
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from src.agents.graph import chat_graph
from src.api.deps import get_current_user, require_admin, require_resident
from src.config import get_settings
from src.database import get_db
from src.models.db import APPLICATION_STATUSES
from src.models.schemas import (
    AdminApplicationResponse,
    ApplicationCreateRequest,
    ApplicationResponse,
    ApplicationStatusUpdateRequest,
    AttachmentResponse,
    AttachmentTypeUpdateRequest,
    ChatHistoryEntry,
    ChatRequest,
    ChatResponse,
    ChecklistItemResponse,
    ChecklistResponse,
    CompletionRequest,
    ConversationSummary,
    CreatedUserResponse,
    CreateUserRequest,
    DashboardResponse,
    DemoAccount,
    OnboardingRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from src.services import storage, store
from src.services.checklist import generate_checklist, only_bql_scope, summarize_progress
from src.services.documents import DOCUMENT_LABELS
from src.services.storage import ALLOWED_CONTENT_TYPES
from src.services.supabase_admin import (
    SupabaseAdminError,
    create_auth_user,
    generate_password,
)
from src.services.vectorstore import RetrievalError

router = APIRouter()


# --- Đăng nhập ----------------------------------------------------------
#
# Xác thực nằm ở Supabase, không ở đây: frontend gọi thẳng
# `supabase.auth.signInWithPassword`, backend chỉ verify JWT (`src/api/deps.py`).
# Endpoint `/auth/login` tra theo email và không kiểm mật khẩu đã bị xoá ngày
# 11/08 — nó trả nguyên hồ sơ cư dân cho bất kỳ ai gọi, và từ lúc frontend
# chuyển sang Supabase thì không còn ai dùng.


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
    """⚠️ TẠM THỜI — các persona tương phản để demo.

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
#
# Các endpoint dưới đây dùng `require_resident`, trừ `GET /profile`: đó là
# endpoint frontend gọi để BIẾT mình là cư dân hay BQL, nên phải mở cho cả hai.


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(user: dict[str, Any] = Depends(get_current_user)) -> Any:
    """US-06 — hồ sơ người đang đăng nhập, cư dân hoặc BQL.

    `onboarding_completed_at = null` là tín hiệu để frontend chuyển hướng
    sang trang onboarding.
    """
    return user


@router.post("/onboarding", response_model=ProfileResponse)
async def submit_onboarding(
    payload: OnboardingRequest,
    user: dict[str, Any] = Depends(require_resident),
    db: Session = Depends(get_db),
) -> Any:
    """US-02 — lưu hồ sơ. Checklist không sinh ở đây mà lọc trực tiếp khi xem."""
    return store.save_onboarding(db, user["user_id"], payload.model_dump())


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    user: dict[str, Any] = Depends(require_resident),
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
    user: dict[str, Any] = Depends(require_resident),
    db: Session = Depends(get_db),
) -> ChecklistResponse:
    """US-04 — checklist cá nhân hóa, tính lại mỗi lần gọi."""
    return _build_checklist(db, user)


@router.patch("/checklist/{item_id}", response_model=ChecklistResponse)
async def set_checklist_item(
    item_id: int,
    payload: CompletionRequest,
    user: dict[str, Any] = Depends(require_resident),
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


# --- Hồ sơ nộp trực tuyến (US-13) ---------------------------------------


@router.post(
    "/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_application(
    payload: ApplicationCreateRequest,
    user: dict[str, Any] = Depends(require_resident),
    db: Session = Depends(get_db),
) -> Any:
    """US-13 — cư dân nộp hồ sơ trực tuyến thay vì mang giấy tờ tới quầy.

    Định tuyến TẤT ĐỊNH: bộ phận xử lý tra từ chính mục checklist, không hỏi
    LLM — cùng lý do đã áp cho rule engine phân loại cư dân.

    Nộp hồ sơ KHÔNG đánh dấu mục checklist là xong: nộp là gửi yêu cầu đi, tick
    là cư dân tự xác nhận đã hoàn tất. Gộp hai việc sẽ khiến tiến độ báo xong
    trong khi BQL còn chưa xử lý.
    """
    matched = generate_checklist(user, store.list_checklist_items(db))
    item = next((i for i in matched if i["id"] == payload.checklist_item_id), None)

    # Không có trong checklist của CHÍNH người này -> 404, kể cả khi mục đó tồn
    # tại với người khác: không xác nhận hộ rằng id đó có thật.
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mục này không có trong checklist của bạn.",
        )

    if store.get_open_application(db, user["user_id"], item["id"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bạn đã có hồ sơ đang xử lý cho “{item['task_name']}”.",
        )

    # Loại hồ sơ suy ra từ THỦ TỤC, không do client khai: mục ngoài phạm vi BQL
    # (tạm trú, cập nhật cư trú) không có bộ phận nào tiếp nhận, nên hồ sơ chỉ
    # là cư dân tự khai kèm ảnh minh chứng.
    kind = "bql_processing" if item["item_type"] == "bql_actionable" else "self_declared"
    return store.create_application(db, user["user_id"], item["id"], payload.note, kind)


@router.post(
    "/applications/{application_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    application_id: int,
    file: UploadFile = File(...),
    document_type: str | None = Form(default=None),
    user: dict[str, Any] = Depends(require_resident),
    db: Session = Depends(get_db),
) -> Any:
    """US-13 — tải ảnh minh chứng lên cho một hồ sơ.

    Tách khỏi `POST /applications` để không phá hợp đồng đã chốt với vai FE:
    tạo hồ sơ bằng JSON như cũ, rồi đính tệp. Với thủ tục ngoài phạm vi BQL
    (tạm trú), chính ảnh này mới là nội dung nộp — không có form nào để điền.

    Tệp vào bucket PRIVATE; đọc lại chỉ qua signed URL hết hạn ngắn. Đây là
    CCCD/VNeID, không bao giờ được có URL công khai.
    """
    app = store.get_application(db, application_id)
    # Không phân biệt "không tồn tại" với "của người khác" — đừng xác nhận hộ
    # rằng id đó có thật.
    if app is None or app.user_id != user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ này."
        )

    # Bỏ trống là hợp lệ — tệp vào diện "chưa phân loại", và hệ thống sẽ KHÔNG
    # kết luận hồ sơ thiếu giấy tờ gì (xem services/documents.py).
    if document_type is not None and document_type not in DOCUMENT_LABELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Loại giấy tờ không hợp lệ. Hợp lệ: {', '.join(DOCUMENT_LABELS)}",
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Chỉ nhận ảnh JPG, PNG hoặc file PDF.",
        )

    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tệp rỗng."
        )
    # Đọc rồi mới đo: `file.size` do client khai, không tin được.
    if len(data) > settings.attachment_max_bytes:
        limit_mb = settings.attachment_max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Tệp vượt quá {limit_mb}MB.",
        )

    path = storage.build_object_path(application_id, file.content_type)
    try:
        storage.upload(path, data, file.content_type)
    except storage.StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Không lưu được tệp lúc này, vui lòng thử lại.",
        ) from exc

    # Chỉ ghi DB SAU khi tệp đã nằm trong bucket: ngược lại sẽ có bản ghi trỏ
    # tới tệp không tồn tại.
    return store.add_attachment(
        db, application_id, storage.display_name(file.filename), file.content_type,
        len(data), path, document_type,
    )


@router.patch(
    "/admin/applications/{application_id}/attachments/{attachment_id}",
    response_model=AttachmentResponse,
)
async def set_attachment_document_type(
    application_id: int,
    attachment_id: int,
    payload: AttachmentTypeUpdateRequest,
    _admin: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """US-13/D1 — Ban quản lý gán lại loại giấy tờ cho một tệp đã tải lên.

    Không phải tiện nghi: gán nhầm (hoặc cư dân chưa gán) thì hồ sơ kẹt ở trạng
    thái "thiếu giấy tờ đã nộp rồi" — BQL nhìn thấy tệp trên màn hình mà hệ thống
    vẫn kêu thiếu, và không ai sửa được. Đây cũng là đường dọn cho những tệp tải
    lên trước khi có `document_type`.
    """
    updated = store.set_attachment_type(
        db, application_id, attachment_id, payload.document_type
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tệp này."
        )
    return updated


@router.get("/applications", response_model=list[ApplicationResponse])
async def list_my_applications(
    user: dict[str, Any] = Depends(require_resident),
    db: Session = Depends(get_db),
) -> Any:
    """US-13 — hồ sơ của chính cư dân, mới nhất trước."""
    return store.list_applications(db, user["user_id"])


# --- Hỏi đáp ------------------------------------------------------------


# Động từ hành chính LLM hay dùng thay cho nhau ("làm thẻ..." / "đăng ký
# thẻ..." / "xin cấp thẻ..." đều chỉ cùng một thủ tục) — bỏ đi trước khi so
# khớp để chỉ còn lại phần lõi (danh từ thủ tục) mang tính phân biệt thật.
_ACTION_PREFIXES = ("dang ky lam ", "dang ky ", "xin cap ", "xin ", "kich hoat ", "lam ")


def _normalize(text: str) -> str:
    """Bỏ dấu + hạ chữ thường — dùng để so tên thủ tục AI đoán với checklist thật."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_marks = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return without_marks.replace("đ", "d")


def _strip_action_prefix(text: str) -> str:
    for prefix in _ACTION_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix) :]
    return text


# Ranh giới mà tool của vai AI cố ý giữ: "cần giấy tờ gì" là câu hỏi THÔNG TIN
# (trả lời bằng chữ là đủ), "cho tôi nộp" là ý định HÀNH ĐỘNG (mới gắn nút).
#
# Phải có cả hai danh sách. Chỉ bắt động từ hành động là chưa đủ: "Làm thẻ xe
# cần giấy tờ gì?" có "làm thẻ" nhưng đuôi câu cho thấy người ta chỉ đang hỏi.
_ACTION_MARKERS = (
    "nop ", "nop ho so", "dan toi", "dua toi", "cho toi nop", "giup toi nop",
    "toi muon lam", "toi muon dang ky", "muon nop", "can nop", "toi nop",
)
_INFO_TAILS = (
    "can giay to gi", "can gi", "gom nhung gi", "gom gi", "la gi",
    "bao nhieu", "the nao", "ra sao", "mat bao lau", "khi nao", "thu tuc gi",
)


def _wants_to_act(question: str) -> bool:
    """True khi câu hỏi là ý định LÀM thủ tục, không phải hỏi về nó."""
    normalized = _normalize(question)
    if any(tail in normalized for tail in _INFO_TAILS):
        return False
    return any(marker in normalized for marker in _ACTION_MARKERS)


def _core_name(text: str) -> str:
    """Phần lõi của tên thủ tục: bỏ dấu, bỏ động từ đầu, bỏ phần trong ngoặc.

    `"Làm thẻ cư dân (chủ hộ)"` → `"the cu dan"`. Phần trong ngoặc phân biệt
    nhánh chủ hộ/người thuê, nhưng hai nhánh đó loại trừ nhau qua `conditions`
    nên trong checklist của MỘT người chỉ có tối đa một mục — bỏ đi để câu hỏi
    tự nhiên vẫn khớp được.
    """
    stripped = _strip_action_prefix(_normalize(text))
    return re.sub(r"\s*\([^)]*\)", "", stripped).strip()


def _match_checklist_item(
    probe: str, items: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Đối chiếu ra ĐÚNG MỘT mục checklist thật, hoặc không gì cả.

    `probe` là tên thủ tục LLM suy ra ("Đăng ký thẻ xe") HOẶC nguyên câu người
    dùng gõ ("Cho tôi nộp hồ sơ làm thẻ cư dân") — cả hai đều đi qua đây kể từ
    12/08, khi lớp đối chiếu thôi phụ thuộc vào việc LLM có gọi tool hay không.

    Khớp từ hai mục trở lên thì trả None: thà không hiện nút còn hơn đưa cư dân
    tới sai thủ tục. `items` đã là checklist RIÊNG của người dùng nên nhánh chủ
    hộ và người thuê không bao giờ cùng xuất hiện.
    """
    probe_core = _core_name(probe)
    if not probe_core:
        return None

    matches = [
        item
        for item in items
        if (core := _core_name(item["task_name"]))
        and (core == probe_core or core in probe_core or probe_core in core)
    ]
    return matches[0] if len(matches) == 1 else None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """US-05 — hỏi đáp thủ tục qua `chat_graph` (RAG). Luôn kèm nguồn, hoặc từ chối.

    Multi-turn (đã chốt với team 13/08, đảo quyết định single-turn ở
    PROJECT_CHARTER.md mục 7): `conversation_id` có giá trị thì tiếp tục hội
    thoại cũ, `chat_graph` được cấp thêm vài lượt gần nhất để viết lại câu hỏi
    mơ hồ ("còn phí thì sao?") thành độc lập ngữ cảnh trước khi truy xuất.
    """
    if payload.conversation_id is not None:
        history = store.get_conversation_messages(db, user["user_id"], payload.conversation_id)
        if not history:
            # Không tồn tại HOẶC không thuộc về người này — cố tình không
            # phân biệt hai trường hợp trong thông báo lỗi (store.py đã ghi
            # rõ lý do), tránh lộ "UUID này có tồn tại" cho người không sở hữu.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy hội thoại này.",
            )
        conversation_id = payload.conversation_id
    else:
        history = []
        conversation_id = uuid.uuid4()

    settings = get_settings()
    recent_turns = [
        {"question": turn["question"], "answer": turn["answer"]}
        for turn in history[-settings.rag_history_turns :]
    ]

    try:
        state = await chat_graph.ainvoke({"query": payload.message, "chat_history": recent_turns})
    except RetrievalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể tra cứu tài liệu lúc này, vui lòng thử lại sau.",
        ) from exc

    result: dict[str, Any] = {
        "answer": state["answer"],
        "sources": state.get("sources", []),
        "answer_source": state["answer_source"],
        "conversation_id": conversation_id,
    }

    # Đối chiếu TẤT ĐỊNH, không phụ thuộc LLM có gọi tool hay không.
    #
    # Trước đây khối này chỉ chạy khi LLM chủ động gọi tool. Đo trên bản deploy
    # 12/08: cùng câu "Dẫn tôi đến chỗ nộp hồ sơ đăng ký thẻ xe" bắn 0/5 lần —
    # và càng bổ sung dữ liệu định tuyến vào KB thì LLM càng trả lời được bằng
    # văn xuôi nên càng ít gọi tool. Dữ liệu tốt lên làm tính năng hỏng đi.
    #
    # Cùng lập luận đã áp cho `sources[]`: việc gì tính tất định được thì không
    # giao cho LLM quyết. Tool hạ xuống thành tín hiệu bổ trợ — vẫn được ưu tiên
    # khi bắn, vì tên thủ tục nó suy ra chính xác hơn nguyên câu hỏi.
    suggested = state.get("suggested_action")
    items = generate_checklist(user, store.list_checklist_items(db))

    # Thử tên do tool suy ra trước (chính xác hơn), không khớp thì thử nguyên
    # câu hỏi. Thiếu bước lùi này thì một lần tool bắn kèm tên lệch sẽ chặn
    # luôn lớp tất định — quan sát được lúc kiểm chứng 12/08.
    match = _match_checklist_item(suggested["procedure_name"], items) if suggested else None
    if match is None and (suggested or _wants_to_act(payload.message)):
        match = _match_checklist_item(payload.message, items)

    if match:
        result["suggested_action"] = {
            "type": "navigate_to_submission",
            "procedure_name": match["task_name"],
            "checklist_item_id": match["id"],
        }
    elif suggested:
        # Tool bắn nhưng không đối chiếu được: giữ hợp đồng ở docs mục 4.4 —
        # vẫn trả về với `checklist_item_id` null để FE tự ẩn nút.
        result["suggested_action"] = {
            "type": suggested["type"],
            "procedure_name": suggested["procedure_name"],
            "checklist_item_id": None,
        }

    store.add_chat(db, user["user_id"], conversation_id, {"question": payload.message, **result})
    return result


@router.get("/chat/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """US-07 — danh sách hội thoại đã lưu của chính người dùng, mới nhất trước."""
    return store.list_conversations(db, user["user_id"])


@router.get("/chat/conversations/{conversation_id}/messages", response_model=list[ChatHistoryEntry])
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """US-07 — toàn bộ lượt hỏi đáp của một hội thoại, để mở lại và hỏi tiếp."""
    messages = store.get_conversation_messages(db, user["user_id"], conversation_id)
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hội thoại này.",
        )
    return messages


# --- Ban quản lý --------------------------------------------------------


@router.post(
    "/admin/users",
    response_model=CreatedUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_resident(
    payload: CreateUserRequest,
    _admin: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """US-00 — BQL tạo tài khoản cư dân. Cư dân không tự đăng ký được.

    Tạo tài khoản Supabase Auth TRƯỚC rồi mới ghi hồ sơ: email trùng sẽ bị
    Supabase chặn ngay, thay vì để lại một hồ sơ không bao giờ đăng nhập được.
    """
    password = generate_password()
    try:
        auth_user_id = create_auth_user(payload.email, password)
    except SupabaseAdminError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không tạo được tài khoản đăng nhập: {exc}",
        ) from exc

    user = store.create_user(db, {**payload.model_dump(), "auth_user_id": auth_user_id})
    return {**user, "temporary_password": password}


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


@router.get("/admin/applications", response_model=list[AdminApplicationResponse])
async def list_applications_for_bql(
    status_filter: str | None = Query(default=None, alias="status"),
    department: str | None = Query(default=None),
    _admin: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """US-13 — hồ sơ cư dân đã nộp, để BQL tiếp nhận và xử lý.

    `?department=An ninh` cho phép mỗi bộ phận chỉ xem phần việc của mình —
    đây chính là chỗ việc "định tuyến" trở nên hữu dụng thay vì chỉ là nhãn.
    """
    if status_filter is not None and status_filter not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Trạng thái không hợp lệ. Hợp lệ: {', '.join(APPLICATION_STATUSES)}",
        )
    return store.list_all_applications(db, status_filter, department)


@router.patch(
    "/admin/applications/{application_id}", response_model=ApplicationResponse
)
async def update_application_status(
    application_id: int,
    payload: ApplicationStatusUpdateRequest,
    _admin: dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """US-13 / D7 — BQL chuyển trạng thái hồ sơ.

    Không ràng buộc thứ tự chuyển trạng thái: quy trình thật có thể quay lại
    (đã duyệt rồi phát hiện thiếu giấy tờ → cần bổ sung). Ép một máy trạng thái
    cứng sẽ chặn đúng những tình huống mà BQL cần xử lý linh hoạt nhất.
    """
    app = store.get_application(db, application_id)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ này."
        )

    # Hồ sơ tự khai KHÔNG có gì để xác nhận ngoài ảnh minh chứng. Ghi nhận một
    # hồ sơ trống nghĩa là BQL xác nhận cư dân đã đăng ký tạm trú mà không hề
    # nhìn thấy bằng chứng nào — đúng thứ mà nguyên tắc "không mạo nhận quy
    # trình của cơ quan khác" cấm.
    if (
        app.kind == "self_declared"
        and payload.status in ("approved", "delivered")
        and store.count_attachments(db, application_id) == 0
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chưa có ảnh minh chứng nào để ghi nhận hồ sơ tự khai này.",
        )

    return store.update_application_status(
        db, application_id, payload.status, payload.bql_note
    )
