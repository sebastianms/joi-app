import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard import Dashboard, DashboardItem
from app.models.user_session import UserSession
from app.models.widget import WidgetORM
from app.repositories.widget_repository import WidgetRepository


def _make_widget(session_id: str, widget_id: str = "w-1") -> WidgetORM:
    return WidgetORM(
        id=widget_id,
        session_id=session_id,
        extraction_id="ext-1",
        widget_type="table",
        selection_source="deterministic",
        render_mode="ui_framework",
        spec_json="{}",
    )


@pytest.fixture
async def repo(db_session: AsyncSession) -> WidgetRepository:
    return WidgetRepository(db_session)


@pytest.fixture
async def session_id(db_session: AsyncSession) -> str:
    s = UserSession(session_id="sess-wr-1")
    db_session.add(s)
    await db_session.flush()
    return s.session_id


@pytest.fixture
async def saved_widget(db_session: AsyncSession, session_id: str) -> WidgetORM:
    w = _make_widget(session_id)
    db_session.add(w)
    await db_session.flush()
    return w


async def test_get_returns_widget(repo: WidgetRepository, saved_widget: WidgetORM, session_id: str):
    result = await repo.get(saved_widget.id, session_id)
    assert result is not None
    assert result.id == saved_widget.id


async def test_get_returns_none_for_wrong_session(repo: WidgetRepository, saved_widget: WidgetORM):
    result = await repo.get(saved_widget.id, "other-session")
    assert result is None


async def test_get_returns_none_for_missing_widget(repo: WidgetRepository, session_id: str):
    result = await repo.get("nonexistent", session_id)
    assert result is None


async def test_mark_saved_sets_fields(repo: WidgetRepository, saved_widget: WidgetORM):
    updated = await repo.mark_saved(saved_widget, "My Widget")
    assert updated.is_saved is True
    assert updated.display_name == "My Widget"
    assert updated.saved_at is not None


async def test_mark_unsaved_clears_fields(repo: WidgetRepository, saved_widget: WidgetORM):
    await repo.mark_saved(saved_widget, "My Widget")
    updated = await repo.mark_unsaved(saved_widget)
    assert updated.is_saved is False
    assert updated.display_name is None
    assert updated.saved_at is None


async def test_list_saved_returns_only_saved(repo: WidgetRepository, db_session: AsyncSession, session_id: str):
    w1 = _make_widget(session_id, "w-saved")
    w2 = _make_widget(session_id, "w-unsaved")
    db_session.add(w1)
    db_session.add(w2)
    await db_session.flush()
    await repo.mark_saved(w1, "Saved")

    results = await repo.list_saved(session_id)
    assert len(results) == 1
    assert results[0].id == "w-saved"


async def test_is_in_any_dashboard_true(repo: WidgetRepository, db_session: AsyncSession, session_id: str, saved_widget: WidgetORM):
    dash = Dashboard(session_id=session_id, name="Dash")
    db_session.add(dash)
    await db_session.flush()
    item = DashboardItem(dashboard_id=dash.id, widget_id=saved_widget.id, grid_x=0, grid_y=0)
    db_session.add(item)
    await db_session.flush()

    assert await repo.is_in_any_dashboard(saved_widget.id) is True


async def test_is_in_any_dashboard_false(repo: WidgetRepository, saved_widget: WidgetORM):
    assert await repo.is_in_any_dashboard(saved_widget.id) is False
