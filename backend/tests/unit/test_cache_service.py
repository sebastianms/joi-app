"""Unit tests for CacheService — covers search, index, invalidation paths."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import ConnectionStatus, DataSourceConnection, DataSourceType
from app.models.user_session import UserSession
from app.models.widget_cache import CacheIndexRequest, WidgetCacheEntryORM
from app.services.widget_cache.cache_service import CacheService


def _doc(entry_id: str = "e1") -> MagicMock:
    doc = MagicMock()
    doc.page_content = "prompt text"
    doc.metadata = {
        "id": entry_id,
        "session_id": "s1",
        "widget_id": "w1",
        "connection_id": "c1",
        "data_schema_hash": "h1",
        "widget_type": "bar",
        "spec_json": "{}",
        "hit_count": 3,
    }
    return doc


async def test_search_returns_candidates_above_threshold(db_session: AsyncSession):
    service = CacheService(db_session)
    fake_vs = MagicMock()
    fake_vs.similarity_search_with_relevance_scores.return_value = [
        (_doc("e1"), 0.91),
        (_doc("e2"), 0.70),  # below threshold
    ]
    with patch.object(service, "_vector_store", return_value=fake_vs):
        results = await service.search(
            session_id="s1", prompt="p", connection_id="c1", data_schema_hash="h1"
        )
    assert len(results) == 1
    assert results[0].entry.id == "e1"
    assert results[0].score == 0.91


async def test_search_degrades_on_vector_store_error(db_session: AsyncSession):
    service = CacheService(db_session)
    with patch.object(service, "_vector_store", side_effect=RuntimeError("qdrant offline")):
        results = await service.search(
            session_id="s", prompt="p", connection_id="c", data_schema_hash="h"
        )
    assert results == []


async def test_index_calls_vector_store(db_session: AsyncSession):
    service = CacheService(db_session)
    fake_vs = MagicMock()
    with patch.object(service, "_vector_store", return_value=fake_vs):
        await service.index(
            CacheIndexRequest(
                entry_id="e1",
                session_id="s1",
                widget_id="w1",
                widget_type="bar",
                spec_json="{}",
                prompt="p",
                connection_id="c1",
                data_schema_hash="h1",
            )
        )
    fake_vs.add_documents.assert_called_once()
    _, kwargs = fake_vs.add_documents.call_args
    assert kwargs["ids"] == ["e1"]


async def test_index_degrades_on_error(db_session: AsyncSession):
    service = CacheService(db_session)
    with patch.object(service, "_vector_store", side_effect=RuntimeError("no qdrant")):
        # Should not raise
        await service.index(
            CacheIndexRequest(
                entry_id="e",
                session_id="s",
                widget_id="w",
                widget_type="bar",
                spec_json="{}",
                prompt="p",
                connection_id="c",
                data_schema_hash="h",
            )
        )


async def test_invalidate_by_connection_soft_deletes_entries(db_session: AsyncSession):
    db_session.add(UserSession(session_id="s-inv"))
    conn = DataSourceConnection(
        user_session_id="s-inv",
        name="c",
        source_type=DataSourceType.SQLITE,
        connection_string="sqlite+aiosqlite:///:memory:",
        status=ConnectionStatus.ACTIVE,
    )
    db_session.add(conn)
    await db_session.flush()

    from app.models.widget import WidgetORM

    widget = WidgetORM(
        id="w-inv",
        session_id="s-inv",
        extraction_id="ext-inv",
        widget_type="bar",
        selection_source="deterministic",
        render_mode="ui_framework",
        spec_json="{}",
    )
    db_session.add(widget)
    entry = WidgetCacheEntryORM(
        id="e-inv",
        session_id="s-inv",
        widget_id="w-inv",
        prompt_text="p",
        data_schema_hash="h",
        connection_id=conn.id,
        widget_type="bar",
    )
    db_session.add(entry)
    await db_session.flush()

    service = CacheService(db_session)
    fake_vs = MagicMock()
    with patch.object(service, "_vector_store", return_value=fake_vs):
        await service.invalidate_by_connection(session_id="s-inv", connection_id=conn.id)
    await db_session.refresh(entry)
    assert entry.invalidated_at is not None
    fake_vs.delete.assert_called_once_with(ids=["e-inv"])


async def test_invalidate_by_connection_noop_when_nothing_active(db_session: AsyncSession):
    service = CacheService(db_session)
    # Should not raise nor try to hit the vector store when nothing to invalidate.
    await service.invalidate_by_connection(session_id="ghost", connection_id="ghost-conn")


async def test_invalidate_tolerates_vector_store_failure(db_session: AsyncSession):
    db_session.add(UserSession(session_id="s-inv2"))
    conn = DataSourceConnection(
        user_session_id="s-inv2",
        name="c",
        source_type=DataSourceType.SQLITE,
        connection_string="sqlite+aiosqlite:///:memory:",
        status=ConnectionStatus.ACTIVE,
    )
    db_session.add(conn)
    await db_session.flush()

    from app.models.widget import WidgetORM

    db_session.add(
        WidgetORM(
            id="w2",
            session_id="s-inv2",
            extraction_id="e2",
            widget_type="bar",
            selection_source="deterministic",
            render_mode="ui_framework",
            spec_json="{}",
        )
    )
    db_session.add(
        WidgetCacheEntryORM(
            id="e2",
            session_id="s-inv2",
            widget_id="w2",
            prompt_text="p",
            data_schema_hash="h",
            connection_id=conn.id,
            widget_type="bar",
        )
    )
    await db_session.flush()

    service = CacheService(db_session)
    with patch.object(service, "_vector_store", side_effect=RuntimeError("qdrant offline")):
        # Should not raise — SQL-side soft delete is enough.
        await service.invalidate_by_connection(session_id="s-inv2", connection_id=conn.id)
