"""Chroma vector store cho RAG (docs/architecture_diagram.md mục 3.5).

Chỉ một collection `documents` ở giai đoạn GATE 2. Collection `faq` hoãn
sang W4, chưa tạo ở đây.
"""

from functools import lru_cache

from langchain_community.vectorstores import Chroma

from src.config import get_settings
from src.services.llm import get_embeddings

_COLLECTION = "documents"


class RetrievalError(RuntimeError):
    """Lỗi hạ tầng khi gọi embeddings hoặc Chroma — không phải "không có dữ liệu".

    Phân biệt với trường hợp truy xuất hợp lệ nhưng rỗng (đó là guard chống
    bịa, trả 200 kèm câu từ chối, không phải lỗi). Route xử lý exception này
    trả HTTP 503, theo docs/architecture_diagram.md mục 5.
    """


@lru_cache
def get_vectorstore() -> Chroma:
    """Một instance dùng chung cho cả process — mở lại Chroma mỗi request là lãng phí."""
    settings = get_settings()
    return Chroma(
        collection_name=_COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
        # Bắt buộc cosine: ngưỡng `rag_max_distance` trong rag_retrieve giả
        # định khoảng cách trả về là cosine distance, không phải L2 mặc định.
        collection_metadata={"hnsw:space": "cosine"},
    )
