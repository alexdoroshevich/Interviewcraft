"""Smoke tests for the FastAPI application."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import app


def _mock_db_ok():
    """DB mock that succeeds on SELECT 1."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=None)
    return db


def test_health_check_db_ok():
    app.dependency_overrides[get_db] = _mock_db_ok
    try:
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "version" in body
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_health_check_db_down():
    """When the DB is unreachable, /health returns 503."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=Exception("connection refused"))
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 503
        assert "Database unreachable" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)
