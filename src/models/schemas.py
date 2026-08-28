"""Pydantic schemas — hợp đồng API giữa backend và frontend.

Đây là nguồn duy nhất định nghĩa shape của request/response. Frontend code
theo file này; đổi field ở đây là đổi hợp đồng, phải báo cả nhóm.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

OwnershipType = Literal["owner", "renter"]
# Khoá tài khoản chặn ở BACKEND, không đụng Supabase Auth: người bị khoá vẫn
# đăng nhập được và vẫn có JWT hợp lệ, nhưng mọi lời gọi API trả 403.
AccountStatus = Literal["active", "locked"]
ApartmentType = Literal["studio", "1pn", "2pn", "3pn", "duplex"]
ItemType = Literal["bql_actionable", "third_party_info"]
DocSourceType = Literal["bql_internal", "public_regulation", "unofficial_web", "synthetic_demo"]
AnswerSource = Literal["faq", "rag", "no_context"]

# Lượt chat thuộc kiểu nào. `qa` là hỏi đáp RAG như cũ; ba giá trị còn lại
# thuộc luồng AI dẫn dắt điền hồ sơ (`src/ai/form_dialog.py`).
#
# Tách khỏi `AnswerSource` có chủ đích: `AnswerSource` được lưu xuống DB dưới
# một SAEnum có ràng buộc, thêm giá trị vào đó là phải migrate. `intent` chỉ
# sống trong một lượt trả lời nên không cần cột riêng.
ChatIntent = Literal["qa", "form_generation", "form_review", "disambiguation"]

# Danh sách đóng, không dùng str tự do: giá trị lệch (vd. "POOL", "swimming")
# sẽ không khớp `conditions` nào và mục tiện ích âm thầm biến mất khỏi
# checklist mà không báo lỗi. Cùng loại rủi ro mà `validate_conditions` phòng
# ở phía dữ liệu seed.
AmenityPackage = Literal["pool", "gym", "tennis", "bbq", "kids_area"]


DocumentType = Literal[
    "cccd", "bien_ban_ban_giao", "hop_dong_thue", "giay_uy_quyen", "dang_ky_xe",
    "the_cu_dan", "the_xe", "don_dang_ky", "to_khai_ct01", "anh_vneid", "khac",
]

EmbedStatus = Literal["pending", "processing", "ready", "failed"]


class RequiredDocument(BaseModel):
    """Một loại giấy tờ, kèm nhãn hiển thị.

    Trả cả `label` chứ không riêng `code`: nếu chỉ trả mã thì frontend lại phải
    giữ một bảng nhãn riêng — đúng chỗ nhân đôi mà D1 đi xoá.
    """

    code: DocumentType
    label: str


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
    required_documents: list[RequiredDocument] = Field(
        default_factory=list,
        description="Giấy tờ thủ tục này yêu cầu; rỗng nghĩa là không đòi gì.",
    )

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


# --- AI Form Generation (Task 1, 20/08) -----------------------------------
#
# Khai trước `ChatRequest`/`ChatResponse` vì hai lớp đó tham chiếu tới
# `FormSchemaPayload`.


class FormFieldSchema(BaseModel):
    """Một trường trong form, định nghĩa bởi AI.

    `pattern` là regex để validate input, vd. '^[0-9]{12}$' cho CCCD.
    """

    key: str
    label: str
    type: Literal["text", "number", "select", "date"]
    options: list[str] | None = None
    required: bool = False
    question: str
    pattern: str | None = None
    default: str | None = None


class AttachmentSpecSchema(BaseModel):
    """Yêu cầu tệp đính kèm cho form.

    `code` là mã loại giấy tờ, phải nằm trong `DocumentType`.
    """

    code: str
    label: str
    required: bool = False


class FormSchemaPayload(BaseModel):
    """Tùy chỉnh form cho một thủ tục, do AI sinh ra."""

    fields: list[FormFieldSchema]
    attachments: list[AttachmentSpecSchema] = []


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

    # Hai trường dưới là toàn bộ trạng thái của luồng AI dẫn dắt điền hồ sơ.
    # Backend không nhớ gì giữa hai lượt: FE nhận `checklist_item_id` và
    # `form_data` ở lượt trước rồi gửi lại nguyên vẹn ở lượt sau. Bỏ trống cả
    # hai thì `/chat` chạy như hỏi đáp thường.
    checklist_item_id: int | None = Field(
        default=None,
        description=(
            "Đang giữa luồng điền hồ sơ của thủ tục này — chép lại từ phản hồi "
            "lượt trước. Bỏ trống để AI tự nhận ý định từ câu hỏi."
        ),
    )
    form_data: dict[str, str] | None = Field(
        default=None,
        description="Các trường đã thu được tới lượt trước, chép lại nguyên vẹn.",
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


class ProcedureOption(BaseModel):
    """Một thủ tục để FE hiển thị khi AI cần cư dân chọn lại."""

    id: int
    task_name: str


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

    # --- Luồng AI dẫn dắt điền hồ sơ ---
    #
    # `intent="qa"` (mặc định) là hỏi đáp thường, ba trường dưới đều null và FE
    # hiển thị y như trước. Khác `qa` thì FE gửi lại `checklist_item_id` +
    # `form_data` ở lượt kế tiếp để nối tiếp hội thoại.
    intent: ChatIntent = Field(
        default="qa",
        description=(
            "`qa` hỏi đáp thường · `form_generation` AI đang hỏi để điền hồ sơ "
            "· `form_review` đã đủ trường, chờ cư dân xem lại và gửi · "
            "`disambiguation` khớp nhiều thủ tục, cư dân chọn một."
        ),
    )
    checklist_item_id: int | None = Field(
        default=None,
        description="Thủ tục đang điền — gửi lại nguyên vẹn ở lượt sau.",
    )
    form_schema: FormSchemaPayload | None = Field(
        default=None,
        description="Định nghĩa form của thủ tục, để FE dựng màn xem lại.",
    )
    form_data: dict[str, str] | None = Field(
        default=None,
        description="Các trường AI đã thu được — gửi lại nguyên vẹn ở lượt sau.",
    )
    options: list[ProcedureOption] = Field(
        default_factory=list,
        description="Các thủ tục có thể chọn khi intent là disambiguation.",
    )

    # US-11 — thêm 26/08. Cộng thêm, có mặc định: FE chưa đọc thì chạy y như cũ.
    #
    # ┌─ Thu đọc mục này ──────────────────────────────────────────────────┐
    # │ `true` → hiện nút "Gửi câu hỏi cho Ban quản lý" dưới câu trả lời.  │
    # │ Bấm nút thì gọi `POST /tickets` (đã có sẵn) với `subject` = chính  │
    # │ câu người dùng vừa hỏi. Backend KHÔNG tự tạo ticket — tạo ngầm mỗi │
    # │ lần AI bí là đẩy rác vào hàng đợi BQL.                             │
    # │                                                                    │
    # │ Chỉ bật cho câu ĐÚNG LĨNH VỰC mà tài liệu thiếu dữ liệu. Câu ngoài │
    # │ lĩnh vực ("công thức nấu phở") vẫn từ chối nhưng `false` — đừng    │
    # │ mời cư dân gửi câu đó cho BQL.                                     │
    # └────────────────────────────────────────────────────────────────────┘
    ticket_suggested: bool = Field(
        default=False,
        description=(
            "Câu hỏi đúng lĩnh vực nhưng tài liệu chưa có đáp án — nên mời cư "
            "dân gửi cho BQL qua `POST /tickets`."
        ),
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
    account_status: AccountStatus


class DashboardResponse(BaseModel):
    """Tiến độ onboarding toàn bộ cư dân.

    Chỉ báo cáo `bql_scope` — BQL cần biết phần việc mình xử lý được đang tới
    đâu, không phải phần thuộc cơ quan khác.
    """

    residents: list[ResidentProgress]
    total_residents: int


# --- Thông báo cư dân ---------------------------------------------------

NotificationKind = Literal["onboarding", "checklist", "needs_info", "rejected"]


class NotificationResponse(BaseModel):
    """Thông báo hành động được tính trực tiếp từ trạng thái thật."""

    id: str
    kind: NotificationKind
    title: str
    message: str
    href: str
    action_label: str


# --- Hồ sơ nộp trực tuyến (US-13) ---------------------------------------

ApplicationStatus = Literal[
    "received", "processing", "needs_info", "approved", "delivered", "rejected"
]

# Hai loại hồ sơ khác bản chất — xem APPLICATION_KINDS trong models/db.py.
# Giao diện PHẢI hiển thị khác nhau: `self_declared` là cư dân tự khai kèm ảnh
# minh chứng cho thủ tục làm ở cơ quan khác, BQL chỉ ghi nhận chứ không xử lý.
ApplicationKind = Literal["bql_processing", "self_declared"]

class AttachmentTypeUpdateRequest(BaseModel):
    """Gán lại loại cho tệp đã tải lên — dùng khi gán nhầm hoặc chưa gán.

    Gửi `null` để trả tệp về trạng thái CHƯA PHÂN LOẠI. Không có đường này thì
    gán nhầm là một chiều: chỉ đổi được sang loại khác, không khôi phục được
    trạng thái trung thực "chưa ai xem" — mà cả tính năng dựa trên việc phân
    biệt hai thứ đó.
    """

    document_type: DocumentType | None


class AttachmentResponse(BaseModel):
    """Ảnh/PDF minh chứng đã tải lên.

    `url` luôn `null` ở đây — xem `GET /api/v1/applications/{id}/attachments/{aid}/url`
    để lấy link đọc tạm thời. Giữ trường này thay vì xoá hẳn để giao diện chưa kịp
    đổi không vỡ vì thiếu khoá; ảnh không hiện thì tốt hơn trang trắng.
    """

    attachment_id: int
    filename: str
    content_type: str
    document_type: DocumentType | None = Field(
        default=None,
        description="`null` = CHƯA phân loại, khác `khac` (đã gán, không thuộc loại nào).",
    )
    size_bytes: int
    url: str | None = None
    uploaded_at: datetime


class AttachmentUrlResponse(BaseModel):
    """Link đọc tạm thời, ký khi người dùng thật sự mở ảnh.

    Tách khỏi phản hồi danh sách vì ký là một lời gọi mạng đồng bộ tới Supabase:
    ký sẵn cho mọi tệp mỗi lần đọc hồ sơ sẽ chặn event loop.
    """

    url: str


class ApplicationCreateRequest(BaseModel):
    """US-13 — cư dân nộp hồ sơ cho một thủ tục trong checklist của chính mình."""

    checklist_item_id: int
    note: str | None = Field(
        default=None,
        max_length=1000,
        description="Ghi chú của cư dân, vd. biển số xe cần đăng ký thẻ.",
    )


class ApplicationCreateV2(BaseModel):
    """US-13 + AI Form Generation — hỗ trợ form_data từ AI sinh."""

    checklist_item_id: int
    note: str | None = None
    form_data: dict | None = None


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
    missing_documents: list[RequiredDocument] | None = Field(
        default=None,
        description=(
            "Giấy tờ còn thiếu. **`null` nghĩa là CHƯA KẾT LUẬN ĐƯỢC** vì hồ sơ "
            "còn tệp chưa phân loại — đừng hiển thị thành 'không thiếu gì'. Khi "
            "đó dùng `unlabelled_count` để nói 'N tệp chưa phân loại'."
        ),
    )
    unlabelled_count: int = 0
    handling_department: str | None = None
    submission_location: str | None = None
    processing_time: str | None = None
    note: str | None = None
    bql_note: str | None = Field(
        default=None, description="Lời nhắn của BQL, vd. lý do cần bổ sung."
    )
    form_data: dict[str, str] = Field(
        default_factory=dict,
        description="Structured form data from AI-assisted submission.",
    )
    created_at: datetime
    updated_at: datetime


class AdminApplicationResponse(ApplicationResponse):
    """Như trên, kèm thông tin cư dân để BQL biết liên hệ ai."""

    user_id: int
    full_name: str
    apartment: str


class ApplicationStatusUpdateRequest(BaseModel):
    """US-13 / D7 — BQL chuyển trạng thái hồ sơ, có thể sửa form_data."""

    status: ApplicationStatus
    bql_note: str | None = Field(
        default=None,
        max_length=1000,
        description=(
            "Bỏ trống thì GIỮ NGUYÊN ghi chú cũ, không xoá — đổi trạng thái mà "
            "không nói gì không nên làm mất lý do 'cần bổ sung' trước đó."
        ),
    )
    form_data: dict[str, str] | None = Field(
        default=None,
        description=(
            "Sửa form_data khi cư dân nhập sai. Bỏ trống (None) thì GIỮ "
            "NGUYÊN form_data cũ. Muốn xoá trắng thì truyền {}."
        ),
    )


# --- Quản lý tài khoản cư dân (18/08) -----------------------------------


class AccountStatusUpdateRequest(BaseModel):
    account_status: AccountStatus


class ResidentDetailResponse(BaseModel):
    """Toàn cảnh một cư dân, cho trang BQL.

    Ghép ba schema đã có thay vì bịa một schema phẳng mới: giao diện đã có sẵn
    component render checklist và hồ sơ ở khu cư dân, nên trang BQL dùng lại
    được, không phải viết lại logic hiển thị.

    Dùng `ApplicationResponse` chứ không phải `AdminApplicationResponse` — đã
    biết đang xem ai thì user_id/full_name/apartment là thừa.
    """

    profile: ProfileResponse
    checklist: ChecklistResponse
    applications: list[ApplicationResponse]
    account_status: AccountStatus


class TemporaryPasswordResponse(BaseModel):
    """Mật khẩu tạm sau khi đặt lại.

    Chỉ xuất hiện đúng một lần ở phản hồi này; hệ thống không lưu và không có
    cách xem lại. Quên nữa thì đặt lại tiếp.
    """

    temporary_password: str


# --- BQL nạp tài liệu (US-08) --------------------------------------------


class DocumentIngestRequest(BaseModel):
    """BQL dán nội dung quy trình mới.

    Dán chữ chứ không tải tệp: `ingest_file` đòi `.md` có frontmatter YAML hợp
    lệ mà BQL không gõ YAML, và đọc PDF nằm ngoài phạm vi. Backend tự sinh
    frontmatter với `source_type: bql_internal`.
    """

    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)

    @field_validator("content")
    @classmethod
    def khong_duoc_toan_khoang_trang(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nội dung tài liệu không được để trống")
        return v


class DocumentResponse(BaseModel):
    document_id: int
    title: str
    file_path: str
    embed_status: EmbedStatus
    uploaded_at: datetime


class DocumentContentResponse(BaseModel):
    """Response for document content endpoint with signed URL."""
    document_id: int
    title: str
    content_type: str = "application/pdf"
    signed_url: str
    expires_at: datetime


# --- Push Subscriptions ---------------------------------------------------


class PushSubscriptionRequest(BaseModel):
    """Register push notification subscription for a device."""

    endpoint: str
    keys: dict[str, str]  # {p256dh, auth}
    user_agent: str | None = None


class PushUnsubscribeRequest(BaseModel):
    """Remove push notification subscription."""

    endpoint: str


# --- Hỗ trợ (Tickets) ---------------------------------------------------

TicketStatus = Literal["open", "in_progress", "resolved", "closed"]
TicketPriority = Literal["low", "normal", "high"]


class TicketCreateRequest(BaseModel):
    """Cư dân tạo ticket hỗ trợ."""

    subject: str = Field(..., min_length=1, max_length=255)
    message: str | None = Field(
        default=None,
        max_length=5000,
        description="Tin nhắn ban đầu (tùy chọn).",
    )


class TicketMessageRequest(BaseModel):
    """Gửi tin nhắn vào ticket."""

    message: str = Field(..., min_length=1, max_length=5000)


class TicketAssignRequest(BaseModel):
    """BQL gán ticket cho nhân viên."""

    assigned_to: int = Field(..., description="User ID của nhân viên được gán.")


class TicketStatusUpdateRequest(BaseModel):
    """BQL cập nhật trạng thái ticket."""

    status: TicketStatus


class TicketResponse(BaseModel):
    """Một ticket hỗ trợ."""

    ticket_id: int
    user_id: int
    subject: str
    status: TicketStatus
    priority: TicketPriority
    assigned_to: int | None = None
    assigned_to_name: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    resolved_at: datetime | None = None


class TicketDetailResponse(TicketResponse):
    """Ticket kèm tin nhắn."""

    last_message: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)


class AdminTicketResponse(TicketResponse):
    """Ticket nhìn từ góc BQL."""

    user_name: str | None = None


# --- Batch Approval (Task 6, Phase 2) -------------------------------------


class BatchApprovalRequest(BaseModel):
    """Duyệt hoặc từ chối nhiều hồ sơ cùng lúc."""

    application_ids: list[int] = Field(
        ...,
        min_length=1,
        description="Danh sách application_id cần xử lý.",
    )
    action: Literal["approve", "reject"] = Field(
        ...,
        description="'approve' -> status = 'approved', 'reject' -> status = 'rejected'.",
    )
    bql_note: str | None = Field(
        default=None,
        max_length=1000,
        description="Ghi chú chung cho tất cả hồ sơ được xử lý.",
    )


class BatchApprovalResult(BaseModel):
    """Một hồ sơ trong kết quả batch."""

    application_id: int
    status: str | None = None
    error: str | None = None


class BatchApprovalResponse(BaseModel):
    """Kết quả batch approval."""

    processed: int = Field(
        ...,
        description="Số hồ sơ xử lý thành công.",
    )
    failed: list[BatchApprovalResult] = Field(
        default_factory=list,
        description="Danh sách hồ sơ thất bại kèm lý do.",
    )
