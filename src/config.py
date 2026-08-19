import re
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

    # Chat LLM — gpt-4o-mini theo stack bắt buộc của charter (mục 8). Chọn
    # đường gọi bằng `CHAT_PROVIDER` trong .env vì mỗi thành viên có key khác
    # nhau; model là một, chỉ khác nhà cung cấp đứng giữa.
    #
    #   openai     — gọi thẳng OpenAI, đúng stack BTC nêu. Cần OPENAI_API_KEY.
    #   openrouter — proxy tương thích OpenAI. Cần OPEN_ROUTER_API_KEY.
    #
    # LƯU Ý tên model: OpenRouter yêu cầu tiền tố "openai/", còn API của OpenAI
    # trả 400 "invalid model ID" nếu có tiền tố đó. `get_chat_llm()` tự thêm
    # tiền tố cho nhánh openrouter — đừng đưa tiền tố vào `chat_model`.
    chat_provider: Literal["openai", "openrouter"] = "openai"
    chat_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    open_router_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_timeout_seconds: float = Field(default=20.0, gt=0)
    # Giới hạn tường minh: mặc định của client là 16k token. Với tài khoản
    # OpenRouter free-tier thì mức đó vượt credit và MỌI request bị 402 dù key
    # hợp lệ. Tài khoản OpenAI trả phí không dính lỗi này, nhưng giữ nguyên
    # giới hạn vì câu trả lời tiếng Việt không cần dài hơn — và để hoá đơn
    # không phụ thuộc vào việc model có nói dài hay không.
    llm_max_tokens: int = Field(default=600, ge=1)

    # Embeddings — OpenRouter không có endpoint embeddings, nên dùng Google
    # Generative AI riêng cho bước embed (query lẫn tài liệu KB). Model
    # "text-embedding-004" đã bị gỡ khỏi API — "gemini-embedding-001" là bản
    # ổn định hiện tại (xác nhận qua ListModels ngày 10/08).
    google_api_key: str = ""
    embedding_model: str = "models/gemini-embedding-001"

    # Database
    #
    # Supabase cho BA chuỗi kết nối khác nhau — chọn sai là mất hàng giờ:
    #   Direct      db.<ref>.supabase.co:5432        → CHỈ IPv6, mạng nhà/văn
    #                                                   phòng IPv4 sẽ treo rồi timeout
    #   Session     <region>.pooler.supabase.com:5432 → DÙNG CÁI NÀY
    #   Transaction <region>.pooler.supabase.com:6543 → pgbouncer transaction mode,
    #                                                   hỏng prepared statement và
    #                                                   DDL trong transaction → Alembic lỗi
    #
    # Mật khẩu có ký tự đặc biệt (@ : / ?) phải URL-encode trong chuỗi.
    database_url: str = "sqlite:///./data/app.db"

    # Supabase Auth (US-01) — lấy ở Project Settings → API.
    # service_role_key có toàn quyền, bỏ qua Row Level Security: chỉ dùng ở
    # backend, KHÔNG bao giờ đưa sang frontend hay commit.
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""

    # US-13 — nơi cất ảnh minh chứng cư dân tải lên. Bucket PRIVATE: giấy tờ
    # tuỳ thân (CCCD, VNeID) không bao giờ được có URL công khai, chỉ đọc qua
    # signed URL hết hạn ngắn do backend ký.
    supabase_storage_bucket: str = "application-attachments"
    attachment_url_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    attachment_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1024)

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

    # Giới hạn tốc độ theo IP (V2/C3, docs/ROLES_AND_PLAN.md) — chỉ chặn burst
    # trên các endpoint TỐN TIỀN: chat gọi LLM + embedding, tải tệp/nạp tài
    # liệu ghi vào storage. KHÔNG có trần tổng số request/ngày ở đây — xem
    # src/services/rate_limit.py để biết lý do.
    chat_rate_limit_per_minute: int = Field(default=10, ge=1)
    chat_rate_limit_per_hour: int = Field(default=100, ge=1)
    upload_rate_limit_per_minute: int = Field(default=20, ge=1)

    # Số lượt hỏi-đáp gần nhất (cùng cuộc hội thoại) đưa vào node `rewrite_query`
    # để viết lại câu hỏi mới thành độc lập ngữ cảnh. Chỉ dùng cho bước viết
    # lại — KHÔNG đưa vào `generate` (xem rewrite_query.py). Lấy ít vì mục
    # đích chỉ là giải quyết đại từ/tỉnh lược ("nó", "còn X thì sao"), không
    # phải tóm tắt cả cuộc hội thoại — lấy nhiều vừa tốn token vừa dễ khiến
    # model bám nhầm vào chủ đề cũ đã hết liên quan.
    rag_history_turns: int = Field(default=3, ge=0, le=10)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def safe_database_url() -> str:
    """`DATABASE_URL` đã che mật khẩu — dùng cho MỌI chỗ in ra màn hình.

    Chuỗi Supabase chứa mật khẩu ngay trong URL. In thẳng ra là đẩy nó vào
    scrollback terminal, log CI và màn hình đang chia sẻ.
    """
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\g<1>***\g<2>", get_settings().database_url)
