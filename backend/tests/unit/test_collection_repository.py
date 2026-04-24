import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSession
from app.models.widget import WidgetORM
from app.repositories.collection_repository import CollectionRepository


@pytest.fixture
async def repo(db_session: AsyncSession) -> CollectionRepository:
    return CollectionRepository(db_session)


@pytest.fixture
async def session_id(db_session: AsyncSession) -> str:
    s = UserSession(session_id="sess-col-1")
    db_session.add(s)
    await db_session.flush()
    return s.session_id


@pytest.fixture
async def widget_id(db_session: AsyncSession, session_id: str) -> str:
    w = WidgetORM(
        id="w-1",
        session_id=session_id,
        extraction_id="ext-1",
        widget_type="table",
        selection_source="deterministic",
        render_mode="ui_framework",
        spec_json="{}",
    )
    db_session.add(w)
    await db_session.flush()
    return w.id


async def test_create_and_list(repo: CollectionRepository, session_id: str):
    await repo.create(session_id, "My Charts")
    await repo.create(session_id, "KPIs")
    collections = await repo.list_by_session(session_id)
    assert len(collections) == 2
    names = {c.name for c in collections}
    assert names == {"My Charts", "KPIs"}


async def test_get_returns_none_for_unknown(repo: CollectionRepository, session_id: str):
    result = await repo.get("no-such-id", session_id)
    assert result is None


async def test_update_name(repo: CollectionRepository, session_id: str):
    c = await repo.create(session_id, "Old Name")
    updated = await repo.update_name(c.id, session_id, "New Name")
    assert updated is not None
    assert updated.name == "New Name"


async def test_delete(repo: CollectionRepository, session_id: str):
    c = await repo.create(session_id, "To Delete")
    deleted = await repo.delete(c.id, session_id)
    assert deleted is True
    assert await repo.get(c.id, session_id) is None


async def test_delete_unknown_returns_false(repo: CollectionRepository, session_id: str):
    assert await repo.delete("ghost", session_id) is False


async def test_add_and_list_widget(
    repo: CollectionRepository, session_id: str, widget_id: str
):
    c = await repo.create(session_id, "Charts")
    await repo.add_widget(c.id, widget_id)
    ids = await repo.list_widget_ids(c.id)
    assert widget_id in ids


async def test_add_widget_idempotent(
    repo: CollectionRepository, session_id: str, widget_id: str
):
    c = await repo.create(session_id, "Charts")
    await repo.add_widget(c.id, widget_id)
    await repo.add_widget(c.id, widget_id)  # second call must not raise
    assert len(await repo.list_widget_ids(c.id)) == 1


async def test_remove_widget(
    repo: CollectionRepository, session_id: str, widget_id: str
):
    c = await repo.create(session_id, "Charts")
    await repo.add_widget(c.id, widget_id)
    await repo.remove_widget(c.id, widget_id)
    assert await repo.list_widget_ids(c.id) == []


async def test_collection_ids_for_widget(
    repo: CollectionRepository, session_id: str, widget_id: str
):
    c1 = await repo.create(session_id, "A")
    c2 = await repo.create(session_id, "B")
    await repo.add_widget(c1.id, widget_id)
    await repo.add_widget(c2.id, widget_id)
    col_ids = await repo.collection_ids_for_widget(widget_id)
    assert set(col_ids) == {c1.id, c2.id}


async def test_session_isolation(repo: CollectionRepository, session_id: str, db_session: AsyncSession):
    other_session = UserSession(session_id="sess-other")
    db_session.add(other_session)
    await db_session.flush()

    await repo.create(session_id, "Mine")
    await repo.create("sess-other", "Theirs")

    mine = await repo.list_by_session(session_id)
    assert len(mine) == 1
    assert mine[0].name == "Mine"
