"""Chốt chặn: lỗi hạ tầng Chroma phải thành `RetrievalError`, không lọt ra thô.

`routes.py` chỉ bắt `RetrievalError` để trả 503 kèm lời giải thích. Bất kỳ
ngoại lệ nào khác lọt ra sẽ rơi vào handler 500 chung, và người dùng nhận
"Đã có lỗi xảy ra" — không phân biệt được "tra cứu tạm hỏng, thử lại sau"
với "sản phẩm có bug".

Lỗi đã có: `get_vectorstore()` nằm NGOÀI khối `try`, nên Chroma hỏng lúc khởi
tạo (thư mục index mất, file .sqlite3 hỏng) thì ném `RuntimeError` thô.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.nodes.rag_retrieve import rag_retrieve_node
from src.services.vectorstore import RetrievalError


@pytest.mark.asyncio
async def test_get_vectorstore_hong_thi_thanh_retrieval_error():
    """Chroma hỏng lúc KHỞI TẠO — điểm hỏng từng lọt ra ngoài try."""
    with patch(
        "src.agents.nodes.rag_retrieve.get_vectorstore",
        side_effect=RuntimeError("Chroma down"),
    ):
        with pytest.raises(RetrievalError):
            await rag_retrieve_node({"query": "Phí gửi xe bao nhiêu?"})


@pytest.mark.asyncio
async def test_similarity_search_hong_thi_thanh_retrieval_error():
    """Embedding hoặc truy vấn hỏng — điểm hỏng đã được bọc từ đầu."""
    fake = MagicMock()
    fake.similarity_search_with_score.side_effect = RuntimeError("embed fail")

    with patch("src.agents.nodes.rag_retrieve.get_vectorstore", return_value=fake):
        with pytest.raises(RetrievalError):
            await rag_retrieve_node({"query": "Phí gửi xe bao nhiêu?"})
