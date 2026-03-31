"""Shared pytest fixtures for InterviewCraft backend tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.redis_client import get_redis


@pytest.fixture
def mock_redis():
    """Mock Redis client — prevents real Redis calls in unit tests."""
    mock = AsyncMock()
    mock.incr = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_db():
    """Mock AsyncSession — prevents real DB calls in unit tests.

    Tests can configure mock_db.execute side effects before making requests:
        mock_db.execute = AsyncMock(return_value=<your_result_mock>)
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
async def client(mock_redis, mock_db):
    """Async test client with Redis and DB dependencies overridden."""
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
