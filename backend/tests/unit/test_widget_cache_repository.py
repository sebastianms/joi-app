import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSession
from app.models.widget import WidgetORM
from app.models.widget_cache import WidgetCacheEntryORM
from app.repositories.widget_cache_repository import WidgetCacheRepository


@pytest.fixture
async def repo(db_session: AsyncSession) -> WidgetCacheRepository:
    return WidgetCacheRepository(db_session)


@pytest.fixture
async def session_id(db_session: AsyncSession) -> str:
    s = UserSession(session_id="sess-cache-1")
    db_session.add(s)
    await db_session.flush()
    return s.session_id


@pytest.fixture
async def widget_id(db_session: AsyncSession, session_id: str) -> str:
    w = WidgetORM(
        id="w-cache-1",
        session_id=session_id,
        extraction_id="ext-1",
        widget_type="bar_chart",
        selection_source="deterministic",
        render_mode="ui_framework",
        spec_json="{}",
    )
    db_session.add(w)
    await db_session.flush()
    return w.id


async def _create_entry(repo: WidgetCacheRepository, session_id: str, widget_id: str, entry_id: str = "entry-1"):
    entry = WidgetCacheEntryORM(
        id=entry_id,
        session_id=session_id,
        widget_id=widget_id,
        prompt_text="show me monthly sales",
        data_schema_hash="abc123",
        connection_id="conn-1",
        widget_type="bar_chart",
    )
    return await repo.create(entry)


async def test_create_and_get(repo: WidgetCacheRepository, session_id: str, widget_id: str):
    entry = await _create_entry(repo, session_id, widget_id)
    fetched = await repo.get(entry.id)
    assert fetched is not None
    assert fetched.prompt_text == "show me monthly sales"
    assert fetched.hit_count == 0


async def test_get_unknown_returns_none(repo: WidgetCacheRepository):
    assert await repo.get("no-such-entry") is None


async def test_increment_hit(repo: WidgetCacheRepository, session_id: str, widget_id: str):
    entry = await _create_entry(repo, session_id, widget_id)
    await repo.increment_hit(entry.id)
    updated = await repo.get(entry.id)
    assert updated.hit_count == 1
    assert updated.last_used_at is not None


async def test_increment_hit_unknown_is_noop(repo: WidgetCacheRepository):
    await repo.increment_hit("ghost")  # must not raise


async def test_soft_delete(repo: WidgetCacheRepository, session_id: str, widget_id: str):
    entry = await _create_entry(repo, session_id, widget_id)
    result = await repo.soft_delete(entry.id)
    assert result is True
    deleted = await repo.get(entry.id)
    assert deleted.invalidated_at is not None


async def test_soft_delete_unknown_returns_false(repo: WidgetCacheRepository):
    assert await repo.soft_delete("ghost") is False


async def test_invalidate_by_connection(
    repo: WidgetCacheRepository, session_id: str, widget_id: str, db_session: AsyncSession
):
    # Create second widget for second entry
    w2 = WidgetORM(
        id="w-cache-2",
        session_id=session_id,
        extraction_id="ext-2",
        widget_type="table",
        selection_source="deterministic",
        render_mode="ui_framework",
        spec_json="{}",
    )
    db_session.add(w2)
    await db_session.flush()

    await _create_entry(repo, session_id, widget_id, "entry-a")
    await repo.create(WidgetCacheEntryORM(
        id="entry-b",
        session_id=session_id,
        widget_id="w-cache-2",
        prompt_text="other query",
        data_schema_hash="def456",
        connection_id="conn-2",
        widget_type="table",
    ))

    invalidated = await repo.invalidate_by_connection(session_id, "conn-1")
    assert "entry-a" in invalidated
    assert "entry-b" not in invalidated

    still_active = await repo.get("entry-b")
    assert still_active.invalidated_at is None
