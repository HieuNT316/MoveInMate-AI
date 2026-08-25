"""Bật LangSmith tracing — deliverable #4 của BTC (V1/E3/B8).

Không có thư viện nào phải gọi: LangChain tự gửi trace khi thấy đúng bộ biến
môi trường. Việc duy nhất cần làm là **đưa cấu hình từ `.env` sang
`os.environ`** — pydantic-settings nạp `.env` vào đối tượng `Settings` chứ
không export ra environ, nên bấy lâu nay ba biến `LANGCHAIN_*` trong
`.env.example` chỉ nằm đó mà không có tác dụng gì.

Bật xong thì mỗi lượt `/chat` hiện thành một trace có đủ ba node
(`rewrite_query` → `rag_retrieve` → `generate`), kèm prompt, số token và độ
trễ từng bước — mở được ngay khi mentor hỏi.
"""

from __future__ import annotations

import logging
import os

from src.config import Settings

logger = logging.getLogger("moveinmate")


def configure_tracing(settings: Settings) -> bool:
    """Export cấu hình LangSmith sang `os.environ`. Trả về đã bật hay chưa.

    Tắt (mặc định) thì **xoá** các biến khỏi environ thay vì để nguyên: máy dev
    có thể còn `LANGCHAIN_TRACING_V2=true` sót lại từ shell trước, và tracing
    bật ngoài ý muốn nghĩa là prompt cùng câu hỏi của cư dân bị gửi ra dịch vụ
    ngoài. Trạng thái mong muốn phải do `.env` quyết, không do môi trường tình cờ.
    """
    if not settings.langchain_tracing_v2:
        for key in ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY", "LANGCHAIN_ENDPOINT"):
            os.environ.pop(key, None)
        return False

    if not settings.langchain_api_key:
        # Bật mà thiếu key thì LangChain ném lỗi ở MỌI lượt gọi LLM. Thà không
        # có trace còn hơn hỏng cả chat vì một thứ chỉ để quan sát.
        logger.warning(
            "langsmith_disabled_missing_key",
            extra={"hint": "LANGCHAIN_TRACING_V2=true nhưng thiếu LANGCHAIN_API_KEY"},
        )
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint

    # Log tên project thôi. `LANGCHAIN_API_KEY` là secret — cùng lý do
    # `safe_database_url()` tồn tại, và repo có hook đẩy log lên server chấm.
    logger.info("langsmith_enabled", extra={"langchain_project": settings.langchain_project})
    return True
