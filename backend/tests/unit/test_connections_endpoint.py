"""HTTP tests for /api/connections endpoints."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.connection import ConnectionStatus


async def test_create_sql_connection_success(client: AsyncClient):
    with patch(
        "app.api.endpoints.connections.ConnectionTesterService.test_connection",
        new=AsyncMock(return_value=(True, None)),
    ):
        res = await client.post(
            "/api/connections/sql",
            json={
                "user_session_id": "sess-conn-1",
                "name": "Local",
                "connection_string": "sqlite+aiosqlite:///:memory:",
                "source_type": "SQLITE",
            },
        )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Local"
    assert data["status"] == ConnectionStatus.ACTIVE.value


async def test_create_sql_connection_rejects_invalid(client: AsyncClient):
    with patch(
        "app.api.endpoints.connections.ConnectionTesterService.test_connection",
        new=AsyncMock(return_value=(False, "bad uri")),
    ):
        res = await client.post(
            "/api/connections/sql",
            json={
                "user_session_id": "sess-conn-1",
                "name": "Broken",
                "connection_string": "sqlite+aiosqlite:///bad",
                "source_type": "SQLITE",
            },
        )
    assert res.status_code == 400
    assert "Connection test failed" in res.json()["detail"]


async def test_upload_json_rejects_non_json_extension(client: AsyncClient):
    res = await client.post(
        "/api/connections/json",
        files={"file": ("nope.txt", b"{}", "text/plain")},
        data={"name": "JSON", "user_session_id": "sess-conn-1"},
    )
    assert res.status_code == 400
    assert "json" in res.json()["detail"].lower()


async def test_upload_json_success(client: AsyncClient, tmp_path):
    fake_path = str(tmp_path / "data.json")
    with patch(
        "app.api.endpoints.connections.JsonFileService.save_and_validate",
        new=AsyncMock(return_value=(fake_path, {})),
    ):
        res = await client.post(
            "/api/connections/json",
            files={"file": ("data.json", b'{"a": 1}', "application/json")},
            data={"name": "Uploaded", "user_session_id": "sess-conn-1"},
        )
    assert res.status_code == 201
    assert res.json()["name"] == "Uploaded"


async def test_upload_json_file_too_large(client: AsyncClient):
    from app.services.json_handler import FileTooLargeError

    with patch(
        "app.api.endpoints.connections.JsonFileService.save_and_validate",
        new=AsyncMock(side_effect=FileTooLargeError("too big")),
    ):
        res = await client.post(
            "/api/connections/json",
            files={"file": ("data.json", b"{}", "application/json")},
            data={"name": "Big", "user_session_id": "sess-conn-1"},
        )
    assert res.status_code == 413


async def test_upload_json_invalid_json(client: AsyncClient):
    from app.services.json_handler import InvalidJsonError

    with patch(
        "app.api.endpoints.connections.JsonFileService.save_and_validate",
        new=AsyncMock(side_effect=InvalidJsonError("bad json")),
    ):
        res = await client.post(
            "/api/connections/json",
            files={"file": ("data.json", b"{", "application/json")},
            data={"name": "Bad", "user_session_id": "sess-conn-1"},
        )
    assert res.status_code == 400


async def test_delete_connection_not_found(client: AsyncClient):
    res = await client.delete("/api/connections/does-not-exist")
    assert res.status_code == 404


async def test_delete_connection_invalidates_cache(client: AsyncClient):
    # Create a connection first via the SQL endpoint
    with patch(
        "app.api.endpoints.connections.ConnectionTesterService.test_connection",
        new=AsyncMock(return_value=(True, None)),
    ):
        create_res = await client.post(
            "/api/connections/sql",
            json={
                "user_session_id": "sess-del-1",
                "name": "ToDelete",
                "connection_string": "sqlite+aiosqlite:///:memory:",
                "source_type": "SQLITE",
            },
        )
    connection_id = create_res.json()["id"]

    mock_invalidate = AsyncMock()
    with patch.object(
        __import__("app.api.endpoints.connections", fromlist=["CacheService"]).CacheService,
        "invalidate_by_connection",
        mock_invalidate,
    ):
        res = await client.delete(f"/api/connections/{connection_id}")

    assert res.status_code == 204
    mock_invalidate.assert_awaited_once_with(
        session_id="sess-del-1", connection_id=connection_id
    )
