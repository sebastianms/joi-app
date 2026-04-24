"""HTTP tests for /api/vector-store endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


async def test_validate_success(client: AsyncClient):
    with patch(
        "app.api.endpoints.vector_store.validate_vector_store",
        return_value=None,
    ):
        res = await client.post(
            "/api/vector-store/validate",
            json={"provider": "qdrant", "connection_params": {"url": "http://x:6333"}},
        )
    assert res.status_code == 200
    assert res.json() == {"valid": True}


async def test_validate_failure_returns_422(client: AsyncClient):
    with patch(
        "app.api.endpoints.vector_store.validate_vector_store",
        side_effect=RuntimeError("bad config"),
    ):
        res = await client.post(
            "/api/vector-store/validate",
            json={"provider": "chroma", "connection_params": {}},
        )
    assert res.status_code == 422
    assert "bad config" in res.json()["detail"]


async def test_save_and_get_config(client: AsyncClient):
    payload = {
        "session_id": "sess-vs-1",
        "provider": "qdrant",
        "connection_params": {"url": "http://x:6333"},
    }
    save_res = await client.post("/api/vector-store/config", json=payload)
    assert save_res.status_code == 201
    saved = save_res.json()
    assert saved["session_id"] == "sess-vs-1"
    assert saved["provider"] == "qdrant"
    assert saved["last_validated_at"] is not None

    get_res = await client.get("/api/vector-store/config", params={"session_id": "sess-vs-1"})
    assert get_res.status_code == 200
    assert get_res.json()["session_id"] == "sess-vs-1"


async def test_get_config_returns_null_when_absent(client: AsyncClient):
    res = await client.get("/api/vector-store/config", params={"session_id": "unknown"})
    assert res.status_code == 200
    assert res.json() is None


async def test_delete_config(client: AsyncClient):
    await client.post(
        "/api/vector-store/config",
        json={
            "session_id": "sess-vs-del",
            "provider": "qdrant",
            "connection_params": {"url": "http://x:6333"},
        },
    )
    res = await client.delete("/api/vector-store/config", params={"session_id": "sess-vs-del"})
    assert res.status_code == 204

    get_res = await client.get("/api/vector-store/config", params={"session_id": "sess-vs-del"})
    assert get_res.json() is None


async def test_delete_config_not_found(client: AsyncClient):
    res = await client.delete("/api/vector-store/config", params={"session_id": "nope"})
    assert res.status_code == 404


async def test_health_default_qdrant_healthy(client: AsyncClient):
    fake_client = MagicMock()
    fake_client.get_collections.return_value = []

    with patch(
        "qdrant_client.QdrantClient",
        return_value=fake_client,
    ):
        res = await client.get("/api/vector-store/health", params={"session_id": "s"})
    data = res.json()
    assert data["provider"] == "qdrant"
    assert data["is_default"] is True
    assert data["healthy"] is True


async def test_health_default_qdrant_unhealthy(client: AsyncClient):
    with patch(
        "qdrant_client.QdrantClient",
        side_effect=RuntimeError("qdrant offline"),
    ):
        res = await client.get("/api/vector-store/health", params={"session_id": "s"})
    assert res.status_code == 200
    assert res.json()["healthy"] is False


async def test_health_byo_config(client: AsyncClient):
    # Save a BYO config first
    await client.post(
        "/api/vector-store/config",
        json={
            "session_id": "sess-health-byo",
            "provider": "qdrant",
            "connection_params": {"url": "http://custom:6333"},
        },
    )

    with patch(
        "app.api.endpoints.vector_store.validate_vector_store",
        return_value=None,
    ):
        res = await client.get(
            "/api/vector-store/health", params={"session_id": "sess-health-byo"}
        )
    data = res.json()
    assert data["provider"] == "qdrant"
    assert data["is_default"] is False
    assert data["healthy"] is True
