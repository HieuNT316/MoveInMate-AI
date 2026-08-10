from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI20K Agent"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000"

    # Chat LLM — gọi qua OpenRouter (API tương thích OpenAI), không gọi thẳng
    # OpenAI. Model giữ nguyên "openai/gpt-4o-mini" để khớp stack bắt buộc của
    # charter (mục 8) — chỉ đổi đường gọi, không đổi model.
    open_router_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    chat_model: str = "openai/gpt-4o-mini"
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_timeout_seconds: float = Field(default=20.0, gt=0)
    # Giới hạn tường minh: mặc định của client (16k) vượt quá số credit của
    # tài khoản OpenRouter free-tier hiện tại, khiến MỌI request bị từ chối
    # với lỗi 402 dù key hợp lệ. Câu trả lời tiếng Việt không cần nhiều token.
    llm_max_tokens: int = Field(default=600, ge=1)

    # Embeddings — OpenRouter không có endpoint embeddings, nên dùng Google
    # Generative AI riêng cho bước embed (query lẫn tài liệu KB). Model
    # "text-embedding-004" đã bị gỡ khỏi API — "gemini-embedding-001" là bản
    # ổn định hiện tại (xác nhận qua ListModels ngày 10/08).
    google_api_key: str = ""
    embedding_model: str = "models/gemini-embedding-001"

    # Database
    database_url: str = "sqlite:///./data/app.db"

    # Vector Store / RAG
    chroma_persist_dir: str = "./data/chroma"
    rag_top_k: int = Field(default=4, ge=1, le=20)

    # Cosine distance Chroma trả về (0 = giống hệt, ~1 = không liên quan).
    # Đoạn khớp gần nhất phải dưới ngưỡng này mới coi là "có context" — vượt
    # ngưỡng thì từ chối thay vì đưa context không liên quan cho LLM.
    #
    # Hiệu chỉnh bằng câu hỏi thật ngày 10/08 (đo trực tiếp trên KB đã ingest,
    # model gemini-embedding-001): câu hỏi có đáp án trong KB (vd. "đăng ký tạm
    # trú thế nào?") ra distance ~0.27-0.33; câu hỏi ngoài phạm vi hoàn toàn
    # (vd. "giá vàng hôm nay?") vẫn ra ~0.37-0.38 chứ không hề cao — hai cụm
    # khá sát nhau. 0.45 (giá trị đoán ban đầu) để lọt cả câu ngoài phạm vi.
    # 0.35 là ngưỡng tách được hai cụm ở mẫu đã thử, nhưng mẫu này CHỈ 4 câu —
    # xem docs/architecture_diagram.md mục 3.5, vẫn cần bộ 10 câu hỏi thật đầy
    # đủ hơn trước khi tin hẳn, và cần thêm dữ liệu KB cho các thủ tục còn
    # thiếu (vd. "thẻ xe" hiện không có tài liệu riêng, dễ bị trả lời lạc đề).
    rag_max_distance: float = Field(default=0.35, ge=0.0, le=2.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
