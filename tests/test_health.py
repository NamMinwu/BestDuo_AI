from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.clients import Clients
from app.config import Settings
from app.main import create_app


@pytest.fixture
def app_with_stub_clients(monkeypatch):
    settings = Settings(
        database_url="postgresql://x:y@localhost/z",
        redis_url="redis://localhost:6379/0",
    )

    async def fake_build(_: Settings) -> Clients:
        return Clients(db=None, redis=None, ollama=AsyncMock(), settings=settings)

    async def fake_close(_: Clients) -> None:
        return None

    monkeypatch.setattr("app.main.build_clients", fake_build)
    monkeypatch.setattr("app.main.close_clients", fake_close)

    async def down(*_, **__):
        return {"status": "down", "error": "stubbed"}

    monkeypatch.setattr("app.main.probe_db", down)
    monkeypatch.setattr("app.main.probe_redis", down)
    monkeypatch.setattr("app.main.probe_ollama", down)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    return create_app()


def test_health_returns_degraded_when_dependencies_down(app_with_stub_clients):
    with TestClient(app_with_stub_clients) as client:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert set(body["checks"].keys()) == {"db", "redis", "ollama"}
