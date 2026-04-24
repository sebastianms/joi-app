"""HTTP tests for /api/health."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


async def test_health_reports_vector_store_healthy(client: AsyncClient):
    fake_client = MagicMock()
    fake_client.get_collections.return_value = []
    with patch("app.api.endpoints.health.QdrantClient", return_value=fake_client):
        res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["vector_store"]["provider"] == "qdrant"
    assert data["vector_store"]["is_default"] is True
    assert data["vector_store"]["healthy"] is True


async def test_health_reports_vector_store_unhealthy(client: AsyncClient):
    with patch("app.api.endpoints.health.QdrantClient", side_effect=RuntimeError("offline")):
        res = await client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["vector_store"]["healthy"] is False
