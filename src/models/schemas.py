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


class OnboardingRequest(BaseModel):
    """US-02 — dữ liệu form onboarding, dùng để lọc checklist."""

    ownership_type: OwnershipType
    apartment_type: ApartmentType
    has_car: bool
    amenity_packages: list[str] = Field(
        default_factory=list,
        description="Gói tiện ích đã đăng ký, vd ['pool', 'gym']",
    )


class ProfileResponse(BaseModel):
    """US-06 — hồ sơ cư dân.

    `onboarding_completed_at` là null khi cư dân chưa điền form; frontend dựa
    vào đó để chuyển hướng sang /onboarding.
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
    amenity_packages: list[str] = Field(default_factory=list)
    onboarding_completed_at: datetime | None = None


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


class ChecklistResponse(BaseModel):
    """US-04 — checklist cá nhân hóa kèm tiến độ."""

    items: list[ChecklistItemResponse]
    total: int
    completed_count: int
    progress_percent: int


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
