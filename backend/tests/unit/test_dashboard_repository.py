import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard import Dashboard
from app.models.user_session import UserSession
from app.models.widget import WidgetORM
from app.repositories.dashboard_repository import DashboardRepository


@pytest.fixture
async def repo(db_session: AsyncSession) -> DashboardRepository:
    return DashboardRepository(db_session)


@pytest.fixture
async def session_id(db_session: AsyncSession) -> str:
    s = UserSession(session_id="sess-dash-1")
    db_session.add(s)
    await db_session.flush()
    return s.session_id


@pytest.fixture
async def widget_id(db_session: AsyncSession, session_id: str) -> str:
    w = WidgetORM(
        id="w-dash-1",
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


async def test_create_and_list(repo: DashboardRepository, session_id: str):
    await repo.create(session_id, "Q1 Sales")
    await repo.create(session_id, "Operations")
    dashboards = await repo.list_by_session(session_id)
    assert len(dashboards) == 2


async def test_get_returns_none_for_unknown(repo: DashboardRepository, session_id: str):
    result = await repo.get("no-such-id", session_id)
    assert result is None


async def test_update_name(repo: DashboardRepository, session_id: str):
    d = await repo.create(session_id, "Old")
    updated = await repo.update_name(d.id, session_id, "New")
    assert updated is not None
    assert updated.name == "New"


async def test_update_name_unknown_returns_none(repo: DashboardRepository, session_id: str):
    result = await repo.update_name("ghost", session_id, "Name")
    assert result is None


async def test_delete(repo: DashboardRepository, session_id: str):
    d = await repo.create(session_id, "Temp")
    deleted = await repo.delete(d.id, session_id)
    assert deleted is True
    assert await repo.get(d.id, session_id) is None


async def test_delete_unknown_returns_false(repo: DashboardRepository, session_id: str):
    assert await repo.delete("ghost", session_id) is False


async def test_add_and_list_items(
    repo: DashboardRepository, session_id: str, widget_id: str
):
    d = await repo.create(session_id, "Sales")
    await repo.add_item(d.id, widget_id, grid_x=0, grid_y=0, width=6, height=4)
    items = await repo.list_items(d.id)
    assert len(items) == 1
    assert items[0].widget_id == widget_id
    assert items[0].width == 6


async def test_remove_item(
    repo: DashboardRepository, session_id: str, widget_id: str
):
    d = await repo.create(session_id, "Sales")
    await repo.add_item(d.id, widget_id)
    await repo.remove_item(d.id, widget_id)
    assert await repo.list_items(d.id) == []


async def test_update_layout_clamps_width(
    repo: DashboardRepository, session_id: str, widget_id: str
):
    d = await repo.create(session_id, "Grid")
    await repo.add_item(d.id, widget_id)
    await repo.update_layout(d.id, [{"widget_id": widget_id, "width": 20}])
    items = await repo.list_items(d.id)
    assert items[0].width == 12  # clamped to max


async def test_update_layout_ignores_unknown_widget(
    repo: DashboardRepository, session_id: str, widget_id: str
):
    d = await repo.create(session_id, "Grid")
    await repo.add_item(d.id, widget_id)
    # Should not raise even if widget_id is not in dashboard
    await repo.update_layout(d.id, [{"widget_id": "no-such-widget", "width": 4}])
    items = await repo.list_items(d.id)
    assert len(items) == 1
