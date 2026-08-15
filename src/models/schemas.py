"""Pydantic schemas — hợp đồng API giữa backend và frontend.

Đây là nguồn duy nhất định nghĩa shape của request/response. Frontend code
theo file này; đổi field ở đây là đổi hợp đồng, phải báo cả nhóm.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

OwnershipType = Literal["owner", "renter"]
ApartmentType = Literal["studio", "1pn", "2pn", "3pn", "duplex"]
ItemType = Literal["bql_actionable", "third_party_info"]
DocSourceType = Literal["bql_internal", "public_regulation", "unofficial_web", "synthetic_demo"]
AnswerSource = Literal["faq", "rag", "no_context"]

# Danh sách đóng, không dùng str tự do: giá trị lệch (vd. "POOL", "swimming")
# sẽ không khớp `conditions` nào và mục tiện ích âm thầm biến mất khỏi
# checklist mà không báo lỗi. Cùng loại rủi ro mà `validate_conditions` phòng
# ở phía dữ liệu seed.
AmenityPackage = Literal["pool", "gym", "tennis", "bbq", "kids_area"]


class OnboardingRequest(BaseModel):
    """US-02 — dữ liệu form onboarding, dùng để lọc checklist."""

    ownership_type: OwnershipType
    apartment_type: ApartmentType
    has_car: bool
    amenity_packages: list[AmenityPackage] = Field(
        default_factory=list,
        description="Gói tiện ích đã đăng ký, vd ['pool', 'gym']",
    )


class ProfileUpdateRequest(BaseModel):
    """US-06 — sửa hồ sơ. Mọi field tuỳ chọn, chỉ gửi phần muốn đổi.

    Tách khỏi `OnboardingRequest` vì đây là PATCH: cư dân báo "vừa mua xe" thì
    chỉ cần gửi `has_car`, không phải gửi lại toàn bộ hồ sơ.
    """

    ownership_type: OwnershipType | None = None
    apartment_type: ApartmentType | None = None
    has_car: bool | None = None
    amenity_packages: list[AmenityPackage] | None = None


class ProfileResponse(BaseModel):
    """US-06 — hồ sơ cư dân.

    `onboarding_completed_at` là null khi cư dân chưa điền form; frontend dựa
    vào đó để chuyển hướng sang /onboarding. Giá trị này chỉ ghi một lần, ở
    lần hoàn thành đầu tiên — sửa hồ sơ về sau không làm nó đổi.
    """

    user_id: int
    full_name: str
    email: str
    apartment: str
    building: str
    role: Literal["resident", "admin"]
    ownership_type: OwnershipType | None = None
    apartment_type: ApartmentType | None = None
    has_car: bool | None = None
    amenity_packages: list[AmenityPackage] = Field(default_factory=list)
    onboarding_completed_at: datetime | None = None


class CreatedUserResponse(ProfileResponse):
    """US-00 — hồ sơ vừa tạo, kèm mật khẩu tạm.

    Mật khẩu chỉ xuất hiện đúng một lần ở phản hồi này để BQL bàn giao cho cư
    dân; hệ thống không lưu lại và không có cách xem lại. Quên thì phải đặt lại.
    """

    temporary_password: str


class DemoAccount(BaseModel):
    """Một tài khoản mẫu cho màn đăng nhập demo, kèm mô tả để chọn nhanh."""

    user_id: int
    full_name: str
    email: str
    role: Literal["resident", "admin"]
    summary: str = Field(description="Mô tả hồ sơ, vd 'Chủ hộ · 2PN · có ô tô · hồ bơi'")
    checklist_total: int = Field(
        description="Số mục checklist rule engine sinh ra cho hồ sơ này — "
        "hai persona khác nhau sẽ ra hai con số khác nhau"
    )


class ChecklistItemResponse(BaseModel):
    """Một mục trong checklist đã lọc theo hồ sơ cư dân.

    `item_type` quyết định cách hiển thị: `third_party_info` là quy trình
    ngoài phạm vi BQL (vd. tạm trú qua công an), frontend cần gắn nhãn rõ.
    """

    id: int
    task_name: str
    description: str
    category: str
    item_type: ItemType
    order_index: int
    completed: bool
    completed_at: datetime | None = None

    # US-13 — định tuyến, đủ để hiện "Bộ phận · Nơi nộp · Thời hạn" ngay trong
    # checklist kể cả khi chưa nộp gì. `null` với `third_party_info`: công an
    # phường xử lý, BQL không tiếp nhận nên không có gì để định tuyến.
    handling_department: str | None = None
    submission_location: str | None = None
    processing_time: str | None = None


class ProgressSummary(BaseModel):
    total: int
    completed: int
    percent: int


class ChecklistResponse(BaseModel):
    """US-04 — checklist cá nhân hóa kèm tiến độ.

    Hai con số tiến độ phục vụ hai đối tượng khác nhau:

    - `overall` — cư dân xem, gồm mọi mục kể cả thủ tục ở cơ quan bên ngoài.
    - `bql_scope` — BQL xem và dùng để đo hiệu quả, chỉ gồm thủ tục BQL thật
      sự xử lý được. Gộp chung hai loại sẽ khiến BQL thấy cư dân "chậm" vì
      một thủ tục mà chính BQL không giúp được và cũng không xác nhận được.
    """

    items: list[ChecklistItemResponse]
    overall: ProgressSummary
    bql_scope: ProgressSummary
    onboarding_completed: bool = Field(
        ...,
        description=(
            "False nghĩa là cư dân chưa điền form, danh sách trả về mới chỉ là "
            "các mục áp dụng cho mọi người. Frontend nên chuyển hướng sang "
            "/onboarding thay vì hiển thị danh sách này."
        ),
    )


class CompletionRequest(BaseModel):
    completed: bool


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: UUID | None = Field(
        default=None,
        description=(
            "Tiếp tục một hội thoại đã có — AI sẽ dùng vài lượt gần nhất của "
            "đúng hội thoại này để hiểu câu hỏi tiếp nối (vd 'còn phí thì "
            "sao?'). Bỏ trống để bắt đầu hội thoại mới."
        ),
    )


class Source(BaseModel):
    """Nguồn trích dẫn — sinh tất định từ bước truy xuất, không do LLM liệt kê."""

    document_id: int
    title: str
    snippet: str
    source_type: DocSourceType


class SuggestedAction(BaseModel):
    """Tín hiệu điều hướng do AI phát hiện khi người dùng hỏi cách nộp hồ sơ.

    `checklist_item_id` có thể null nếu backend không đối chiếu được
    `procedure_name` (do AI suy ra, có thể lệch chữ) với đúng một mục trong
    checklist thật của người dùng — FE nên ẩn nút điều hướng trong trường
    hợp đó, chỉ hiển thị `procedure_name` dạng text.

    Từ 15/08 đích điều hướng đã có thật: `POST /api/v1/applications` (US-13).
    FE có thể dẫn thẳng tới form nộp hồ sơ của đúng `checklist_item_id`, thay
    vì chỉ mở `/checklist` như giai đoạn trước.
    """

    type: Literal["navigate_to_submission"]
    procedure_name: str
    checklist_item_id: int | None = None


class ChatResponse(BaseModel):
    """US-05 — câu trả lời kèm nguồn.

    `answer_source` cho biết câu trả lời đến từ đâu; `no_context` nghĩa là
    không tìm được tài liệu phù hợp nên hệ thống từ chối trả lời thay vì bịa.
    """

    answer: str
    sources: list[Source] = Field(default_factory=list)
    answer_source: AnswerSource
    suggested_action: SuggestedAction | None = None
    conversation_id: UUID = Field(
        description="Hội thoại vừa hỏi thuộc về — FE cần lưu lại để gửi kèm "
        "cho câu hỏi tiếp theo nếu muốn AI hiểu ngữ cảnh."
    )


class ChatHistoryEntry(BaseModel):
    """Một lượt hỏi đáp đã lưu, thuộc về đúng một hội thoại."""

    id: int
    question: str
    answer: str
    answer_source: AnswerSource
    sources: list[Source] = Field(default_factory=list)
    created_at: datetime


class ConversationSummary(BaseModel):
    """US-07 — một cuộc hội thoại đã lưu, hiển thị trong danh sách để bấm vào
    xem lại/hỏi tiếp. `preview` lấy nguyên câu hỏi đầu tiên làm tiêu đề."""

    conversation_id: UUID
    preview: str
    message_count: int
    last_message_at: datetime


class CreateUserRequest(BaseModel):
    """US-00 — BQL tạo tài khoản cho cư dân. Cư dân không tự đăng ký được."""

    full_name: str = Field(..., min_length=1)
    email: str
    apartment: str
    building: str


class ResidentProgress(BaseModel):
    """Một dòng trong dashboard BQL."""

    user_id: int
    full_name: str
    apartment: str
    ownership_type: OwnershipType | None
    onboarded: bool
    bql_scope: ProgressSummary


class DashboardResponse(BaseModel):
    """Tiến độ onboarding toàn bộ cư dân.

    Chỉ báo cáo `bql_scope` — BQL cần biết phần việc mình xử lý được đang tới
    đâu, không phải phần thuộc cơ quan khác.
    """

    residents: list[ResidentProgress]
    total_residents: int


# --- Hồ sơ nộp trực tuyến (US-13) ---------------------------------------

ApplicationStatus = Literal[
    "received", "processing", "needs_info", "approved", "delivered", "rejected"
]

# Hai loại hồ sơ khác bản chất — xem APPLICATION_KINDS trong models/db.py.
# Giao diện PHẢI hiển thị khác nhau: `self_declared` là cư dân tự khai kèm ảnh
# minh chứng cho thủ tục làm ở cơ quan khác, BQL chỉ ghi nhận chứ không xử lý.
ApplicationKind = Literal["bql_processing", "self_declared"]


class AttachmentResponse(BaseModel):
    """Ảnh/PDF minh chứng đã tải lên.

    `url` là link ĐỌC TẠM THỜI, ký lại mỗi lần đọc và hết hạn sau vài phút —
    đừng lưu lại hay chia sẻ. `null` nghĩa là ký link hỏng, thử tải lại trang.
    """

    attachment_id: int
    filename: str
    content_type: str
    size_bytes: int
    url: str | None = None
    uploaded_at: datetime


class ApplicationCreateRequest(BaseModel):
    """US-13 — cư dân nộp hồ sơ cho một thủ tục trong checklist của chính mình."""

    checklist_item_id: int
    note: str | None = Field(
        default=None,
        max_length=1000,
        description="Ghi chú của cư dân, vd. biển số xe cần đăng ký thẻ.",
    )


class ApplicationResponse(BaseModel):
    """Một hồ sơ đã nộp.

    Ba trường định tuyến tra thẳng từ checklist item chứ không sao chép vào hồ
    sơ — bảng định tuyến đổi thì hồ sơ cũ hiện đúng ngay.
    """

    application_id: int
    checklist_item_id: int
    task_name: str
    status: ApplicationStatus
    kind: ApplicationKind = Field(
        description=(
            "`bql_processing` — Ban quản lý thật sự xử lý. `self_declared` — thủ "
            "tục làm ở cơ quan khác, cư dân tự nộp ảnh minh chứng và BQL chỉ ghi "
            "nhận. Giao diện không được nói 'Ban quản lý đang xử lý' với loại sau."
        )
    )
    attachments: list[AttachmentResponse] = Field(default_factory=list)
    handling_department: str | None = None
    submission_location: str | None = None
    processing_time: str | None = None
    note: str | None = None
    bql_note: str | None = Field(
        default=None, description="Lời nhắn của BQL, vd. lý do cần bổ sung."
    )
    created_at: datetime
    updated_at: datetime


class AdminApplicationResponse(ApplicationResponse):
    """Như trên, kèm thông tin cư dân để BQL biết liên hệ ai."""

    user_id: int
    full_name: str
    apartment: str


class ApplicationStatusUpdateRequest(BaseModel):
    """US-13 / D7 — BQL chuyển trạng thái hồ sơ."""

    status: ApplicationStatus
    bql_note: str | None = Field(
        default=None,
        max_length=1000,
        description=(
            "Bỏ trống thì GIỮ NGUYÊN ghi chú cũ, không xoá — đổi trạng thái mà "
            "không nói gì không nên làm mất lý do 'cần bổ sung' trước đó."
        ),
    )
