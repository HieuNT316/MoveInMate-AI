"""Pydantic schemas — hợp đồng API giữa backend và frontend.

Đây là nguồn duy nhất định nghĩa shape của request/response. Frontend code
theo file này; đổi field ở đây là đổi hợp đồng, phải báo cả nhóm.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

OwnershipType = Literal["owner", "renter"]
ApartmentType = Literal["studio", "1pn", "2pn", "3pn", "duplex"]
ItemType = Literal["bql_actionable", "third_party_info"]
DocSourceType = Literal["bql_internal", "public_regulation"]
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


class LoginRequest(BaseModel):
    """⚠️ TẠM THỜI — đăng nhập chỉ bằng email, chưa có mật khẩu.

    Supabase Auth là nguồn xác thực duy nhất đã chốt (charter mục 7), nhưng
    project Supabase chưa dựng. Endpoint này tồn tại để demo được nhiều persona
    thay vì hardcode user id ở frontend, và phải xoá khi có Supabase Auth.
    """

    email: str


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


class Source(BaseModel):
    """Nguồn trích dẫn — sinh tất định từ bước truy xuất, không do LLM liệt kê."""

    document_id: int
    title: str
    snippet: str
    source_type: DocSourceType


class ChatResponse(BaseModel):
    """US-05 — câu trả lời kèm nguồn.

    `answer_source` cho biết câu trả lời đến từ đâu; `no_context` nghĩa là
    không tìm được tài liệu phù hợp nên hệ thống từ chối trả lời thay vì bịa.
    """

    answer: str
    sources: list[Source] = Field(default_factory=list)
    answer_source: AnswerSource


class ChatHistoryEntry(BaseModel):
    """US-07 — một lượt hỏi đáp đã lưu."""

    id: int
    question: str
    answer: str
    answer_source: AnswerSource
    sources: list[Source] = Field(default_factory=list)
    created_at: datetime


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
