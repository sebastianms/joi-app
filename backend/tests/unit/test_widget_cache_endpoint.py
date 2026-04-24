"""HTTP tests for /api/widget-cache endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSession
from app.models.widget_cache import CacheCandidate, WidgetCacheEntry, WidgetCacheEntryORM


def _candidate(entry_id: str = "entry-1", score: float = 0.91) -> CacheCandidate:
    return CacheCandidate(
        entry=WidgetCacheEntry(
            id=entry_id,
            session_id="sess-cache-1",
            widget_id="widget-1",
            prompt_text="ventas por mes",
            data_schema_hash="hash123",
            connection_id="conn-1",
            widget_type="bar",
            hit_count=2,
        ),
        score=score,
        widget_spec_json="{}",
    )


async def test_search_endpoint_returns_candidates(client: AsyncClient):
    mock_search = AsyncMock(return_value=[_candidate()])
    with patch(
        "app.api.endpoints.widget_cache.CacheService.search",
        mock_search,
    ):
        res = await client.post(
            "/api/widget-cache/search",
            json={
                "session_id": "sess-cache-1",
                "prompt": "ventas por mes",
                "connection_id": "conn-1",
                "data_schema_hash": "hash123",
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["cache_entry_id"] == "entry-1"
    assert data["candidates"][0]["widget_type"] == "bar"


async def test_search_endpoint_empty(client: AsyncClient):
    with patch(
        "app.api.endpoints.widget_cache.CacheService.search",
        AsyncMock(return_value=[]),
    ):
        res = await client.post(
            "/api/widget-cache/search",
            json={
                "session_id": "s",
                "prompt": "x",
                "connection_id": "c",
                "data_schema_hash": "h",
            },
        )
    assert res.status_code == 200
    assert res.json()["candidates"] == []


@pytest.fixture
async def cache_entry(db_session: AsyncSession) -> WidgetCacheEntryORM:
    from app.models.user_session import UserSession
    from app.models.connection import DataSourceConnection, DataSourceType, ConnectionStatus
    from app.models.widget import WidgetORM

    db_session.add(UserSession(session_id="sess-reuse-1"))
    conn = DataSourceConnection(
        user_session_id="sess-reuse-1",
        name="c",
        source_type=DataSourceType.SQLITE,
        connection_string="sqlite+aiosqlite:///:memory:",
        status=ConnectionStatus.ACTIVE,
    )
    db_session.add(conn)
    await db_session.flush()

    widget = WidgetORM(
        id="widget-reuse-1",
        session_id="sess-reuse-1",
        extraction_id="ext-1",
        widget_type="bar",
        selection_source="deterministic",
        render_mode="ui_framework",
        spec_json="{}",
    )
    db_session.add(widget)
    await db_session.flush()

    entry = WidgetCacheEntryORM(
        id="entry-reuse-1",
        session_id="sess-reuse-1",
        widget_id=widget.id,
        prompt_text="p",
        data_schema_hash="h",
        connection_id=conn.id,
        widget_type="bar",
    )
    db_session.add(entry)
    await db_session.flush()
    return entry


async def test_reuse_increments_hit_count(client: AsyncClient, cache_entry: WidgetCacheEntryORM):
    res = await client.post(
        f"/api/widget-cache/{cache_entry.id}/reuse",
        json={"session_id": "sess-reuse-1"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["widget_id"] == cache_entry.widget_id
    assert data["hit_count"] == 1


async def test_reuse_not_found(client: AsyncClient):
    res = await client.post(
        "/api/widget-cache/nope/reuse",
        json={"session_id": "s"},
    )
    assert res.status_code == 404


async def test_reuse_session_mismatch(client: AsyncClient, cache_entry: WidgetCacheEntryORM):
    res = await client.post(
        f"/api/widget-cache/{cache_entry.id}/reuse",
        json={"session_id": "other-session"},
    )
    assert res.status_code == 403


async def test_delete_cache_entry(client: AsyncClient, cache_entry: WidgetCacheEntryORM):
    with patch(
        "app.api.endpoints.widget_cache.CacheService._vector_store",
        MagicMock(side_effect=RuntimeError("qdrant offline — OK, soft delete still applies")),
    ):
        res = await client.delete(
            f"/api/widget-cache/{cache_entry.id}",
            params={"session_id": "sess-reuse-1"},
        )
    assert res.status_code == 204


async def test_delete_cache_entry_not_found(client: AsyncClient):
    res = await client.delete(
        "/api/widget-cache/nope",
        params={"session_id": "s"},
    )
    assert res.status_code == 404


async def test_delete_cache_entry_session_mismatch(
    client: AsyncClient, cache_entry: WidgetCacheEntryORM
):
    res = await client.delete(
        f"/api/widget-cache/{cache_entry.id}",
        params={"session_id": "wrong"},
    )
    assert res.status_code == 403
