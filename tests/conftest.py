from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.services import mock_store


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def reset_store():
    """Trả `mock_store` về trạng thái ban đầu sau mỗi test.

    Store hiện là biến module-level nên test sẽ ảnh hưởng lẫn nhau nếu không
    khôi phục. Fixture này biến mất cùng `mock_store` khi chuyển sang DB thật.
    """
    snapshot = (
        deepcopy(mock_store._USERS),
        deepcopy(mock_store._COMPLETIONS),
        deepcopy(mock_store._CHAT_HISTORY),
    )
    yield
    mock_store._USERS, mock_store._COMPLETIONS, mock_store._CHAT_HISTORY = snapshot


@pytest.fixture
def mock_llm():
    """Mock LLM to avoid calling OpenAI during tests.

    Usage in test:
        def test_something(mock_llm):
            # LLM calls will return mock response instead of hitting OpenAI
            ...
    """
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
