"""Stub hỏi đáp cho bản demo luồng.

⚠️ TẠM THỜI — sẽ được thay bằng `chat_graph` thật (RAG trên Chroma) do role AI
phụ trách. File này chỉ tồn tại để luồng chạy được trước khi có KB.

Giữ đúng shape response của bản thật, nên khi thay ruột thì frontend không
phải sửa gì. Hai hành vi được mô phỏng có chủ đích:

1. Câu trả lời luôn kèm nguồn trích dẫn.
2. Câu hỏi ngoài phạm vi tài liệu thì **từ chối trả lời**, không bịa — đây là
   ràng buộc của đề bài và là bảo đảm kỹ thuật, không phải lời dặn trong prompt.
"""

import unicodedata
from typing import Any

REFUSAL = (
    "Xin lỗi, tôi chưa tìm thấy thông tin này trong tài liệu hiện có. "
    "Bạn vui lòng liên hệ Ban quản lý toà nhà để được hỗ trợ chính xác."
)

# Mỗi mục: từ khoá nhận diện → câu trả lời + nguồn trích dẫn.
_CANNED: list[dict[str, Any]] = [
    {
        "keywords": ("thẻ xe", "gửi xe", "ô tô", "oto", "xe máy", "đỗ xe"),
        "answer": (
            "Để đăng ký thẻ xe, bạn nộp hồ sơ tại văn phòng Ban quản lý gồm: "
            "giấy đăng ký xe (bản sao), CCCD và thẻ cư dân đã được cấp. "
            "Thời gian xử lý thường trong 1-3 ngày làm việc."
        ),
        "sources": [
            {
                "document_id": 1,
                "title": "Quy trình đăng ký thẻ xe — Vinhomes Smart City",
                "snippet": "Hồ sơ đăng ký thẻ xe gồm giấy đăng ký xe, CCCD và thẻ cư dân...",
                "source_type": "bql_internal",
            }
        ],
    },
    {
        "keywords": ("thẻ cư dân", "giấy tờ", "hồ sơ cư dân"),
        "answer": (
            "Hồ sơ làm thẻ cư dân khác nhau tuỳ bạn là chủ hộ hay người thuê. "
            "Chủ hộ cần CCCD kèm giấy tờ chứng minh quyền sở hữu căn hộ. "
            "Người thuê cần thêm hợp đồng thuê nhà và giấy uỷ quyền của chủ hộ. "
            "Cả hai trường hợp đều cần ảnh 3x4."
        ),
        "sources": [
            {
                "document_id": 2,
                "title": "Quy trình cấp thẻ cư dân",
                "snippet": "Chủ sở hữu: CCCD + giấy tờ căn hộ + ảnh 3x4. Khách thuê: bổ sung hợp đồng thuê...",
                "source_type": "bql_internal",
            }
        ],
    },
    {
        "keywords": ("tạm trú", "lưu trú", "cư trú", "công an"),
        "answer": (
            "Đăng ký tạm trú không thuộc phạm vi xử lý của Ban quản lý mà do cơ quan "
            "công an phường tiếp nhận. Theo quy định hiện hành, bạn cần khai báo trong "
            "vòng 30 ngày kể từ khi đến ở, qua ứng dụng VNeID hoặc trực tiếp tại công an "
            "phường nơi cư trú."
        ),
        "sources": [
            {
                "document_id": 3,
                "title": "Luật Cư trú 2020 — quy định về đăng ký tạm trú",
                "snippet": "Người đến sinh sống tại chỗ ở hợp pháp ngoài nơi thường trú phải đăng ký tạm trú...",
                "source_type": "public_regulation",
            }
        ],
    },
    {
        "keywords": ("hồ bơi", "gym", "tiện ích", "bể bơi"),
        "answer": (
            "Thẻ tiện ích được kích hoạt tại quầy lễ tân khu tiện ích sau khi bạn đã có "
            "thẻ cư dân. Bạn mang theo thẻ cư dân và xác nhận gói tiện ích đã đăng ký "
            "trong hợp đồng."
        ),
        "sources": [
            {
                "document_id": 4,
                "title": "Hướng dẫn sử dụng tiện ích nội khu",
                "snippet": "Cư dân kích hoạt thẻ tiện ích tại quầy lễ tân, xuất trình thẻ cư dân...",
                "source_type": "bql_internal",
            }
        ],
    },
]


def _strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt để khớp được cả khi người dùng gõ không dấu.

    Nhiều người gõ "the xe" thay vì "thẻ xe". Không chuẩn hoá thì hệ thống từ
    chối một câu hỏi nó biết trả lời — nhìn như hỏng.
    """
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_marks = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return without_marks.replace("đ", "d")


def answer_question(message: str) -> dict[str, Any]:
    """Trả lời dựa trên từ khoá; không khớp thì từ chối thay vì bịa."""
    text = _strip_accents(message)
    for entry in _CANNED:
        if any(_strip_accents(keyword) in text for keyword in entry["keywords"]):
            return {
                "answer": entry["answer"],
                "sources": entry["sources"],
                "answer_source": "rag",
            }
    return {"answer": REFUSAL, "sources": [], "answer_source": "no_context"}
