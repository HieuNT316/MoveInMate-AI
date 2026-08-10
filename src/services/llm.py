"""Client cho hai mô hình khác nhau dùng trong RAG.

Chat và embeddings đến từ hai nhà cung cấp khác nhau có chủ đích: OpenRouter
không có endpoint embeddings, nên chat đi qua OpenRouter (tương thích API
OpenAI, giữ đúng model `openai/gpt-4o-mini` theo charter) còn embeddings gọi
thẳng Google Generative AI.
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI

from src.config import get_settings


def get_chat_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.chat_model,
        api_key=settings.open_router_api_key,
        base_url=settings.openrouter_base_url,
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
