"""Client cho hai mô hình khác nhau dùng trong RAG.

Chat dùng gpt-4o-mini, gọi thẳng OpenAI hoặc qua OpenRouter tuỳ `CHAT_PROVIDER`
— cùng một model, chỉ khác đường đi (xem `src/config.py`).

Embeddings thì phải là Google Generative AI: toàn bộ index Chroma hiện tại
được embed bằng `gemini-embedding-001`. Đổi nhà cung cấp embedding mà không
ingest lại từ đầu sẽ khiến vector lúc truy vấn nằm khác không gian với vector
lúc index, và retrieval trả về rác một cách IM LẶNG.
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI

from src.config import get_settings


def get_chat_llm() -> ChatOpenAI:
    settings = get_settings()

    if settings.chat_provider == "openrouter":
        # OpenRouter định danh model theo dạng "<hãng>/<model>".
        api_key, base_url = settings.open_router_api_key, settings.openrouter_base_url
        model = f"openai/{settings.chat_model}"
    else:
        # base_url=None để client dùng endpoint mặc định của OpenAI.
        api_key, base_url = settings.openai_api_key, None
        model = settings.chat_model

    if not api_key:
        raise RuntimeError(
            f"CHAT_PROVIDER={settings.chat_provider} nhưng thiếu API key tương ứng "
            "trong .env. Xem .env.example."
        )

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
        max_tokens=settings.llm_max_tokens,
    )


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    settings = get_settings()
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )
