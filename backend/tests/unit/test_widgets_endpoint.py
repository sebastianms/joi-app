import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard import Dashboard, DashboardItem
from app.models.user_session import UserSession
from app.models.widget import WidgetORM


def _make_widget(session_id: str, selection_source: str = "deterministic", widget_id: str = "w-ep-1") -> WidgetORM:
    return WidgetORM(
        id=widget_id,
        session_id=session_id,
        extraction_id="ext-1",
        widget_type="table",
        selection_source=selection_source,
        render_mode="ui_framework",
        spec_json="{}",
    )


@pytest.fixture
async def session_id(db_session: AsyncSession) -> str:
    s = UserSession(session_id="sess-ep-1")
    db_session.add(s)
    await db_session.flush()
    return s.session_id


@pytest.fixture
async def widget(db_session: AsyncSession, session_id: str) -> WidgetORM:
    w = _make_widget(session_id)
    db_session.add(w)
    await db_session.flush()
    return w


async def test_save_widget_returns_200(client: AsyncClient, widget: WidgetORM, session_id: str):
    res = await client.post(f"/api/widgets/{widget.id}/save", json={
        "session_id": session_id,
        "display_name": "My Chart",
        "collection_ids": [],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_saved"] is True
    assert data["display_name"] == "My Chart"


async def test_save_widget_404_on_missing(client: AsyncClient, session_id: str):
    res = await client.post("/api/widgets/nonexistent/save", json={
        "session_id": session_id,
        "display_name": "X",
        "collection_ids": [],
    })
    assert res.status_code == 404


async def test_save_widget_duplicate_name_returns_409(client: AsyncClient, db_session: AsyncSession, session_id: str):
    w1 = _make_widget(session_id, widget_id="w-dup-1")
    w2 = _make_widget(session_id, widget_id="w-dup-2")
    db_session.add(w1)
    db_session.add(w2)
    await db_session.flush()

    res1 = await client.post("/api/widgets/w-dup-1/save", json={
        "session_id": session_id,
        "display_name": "Duplicado",
        "collection_ids": [],
    })
    assert res1.status_code == 200

    res2 = await client.post("/api/widgets/w-dup-2/save", json={
        "session_id": session_id,
        "display_name": "Duplicado",
        "collection_ids": [],
    })
    assert res2.status_code == 409
    assert "Duplicado" in res2.json()["detail"]


async def test_save_fallback_widget_returns_422(client: AsyncClient, db_session: AsyncSession, session_id: str):
    fallback = _make_widget(session_id, selection_source="fallback", widget_id="w-fallback")
    db_session.add(fallback)
    await db_session.flush()

    res = await client.post(f"/api/widgets/{fallback.id}/save", json={
        "session_id": session_id,
        "display_name": "Fallback",
        "collection_ids": [],
    })
    assert res.status_code == 422


async def test_unsave_widget_returns_204(client: AsyncClient, widget: WidgetORM, session_id: str):
    await client.post(f"/api/widgets/{widget.id}/save", json={
        "session_id": session_id,
        "display_name": "Temp",
        "collection_ids": [],
    })
    res = await client.delete(f"/api/widgets/{widget.id}/save", params={"session_id": session_id})
    assert res.status_code == 204


async def test_unsave_widget_404_on_missing(client: AsyncClient, session_id: str):
    res = await client.delete("/api/widgets/nonexistent/save", params={"session_id": session_id})
    assert res.status_code == 404


async def test_unsave_widget_409_if_in_dashboard(
    client: AsyncClient, db_session: AsyncSession, widget: WidgetORM, session_id: str
):
    await client.post(f"/api/widgets/{widget.id}/save", json={
        "session_id": session_id,
        "display_name": "In Dashboard",
        "collection_ids": [],
    })
    dash = Dashboard(session_id=session_id, name="D1")
    db_session.add(dash)
    await db_session.flush()
    item = DashboardItem(dashboard_id=dash.id, widget_id=widget.id, grid_x=0, grid_y=0)
    db_session.add(item)
    await db_session.flush()

    res = await client.delete(f"/api/widgets/{widget.id}/save", params={"session_id": session_id})
    assert res.status_code == 409


async def test_save_widget_with_collection(client: AsyncClient, widget: WidgetORM, session_id: str):
    col_res = await client.post("/api/collections", json={"session_id": session_id, "name": "My Col"})
    collection_id = col_res.json()["id"]

    res = await client.post(f"/api/widgets/{widget.id}/save", json={
        "session_id": session_id,
        "display_name": "Grouped Chart",
        "collection_ids": [collection_id],
    })
    assert res.status_code == 200
    assert collection_id in res.json()["collection_ids"]


async def test_save_widget_invalid_collection_returns_404(client: AsyncClient, widget: WidgetORM, session_id: str):
    res = await client.post(f"/api/widgets/{widget.id}/save", json={
        "session_id": session_id,
        "display_name": "Chart",
        "collection_ids": ["nonexistent-col"],
    })
    assert res.status_code == 404


async def test_unsave_widget_removes_from_collection(client: AsyncClient, widget: WidgetORM, session_id: str):
    col_res = await client.post("/api/collections", json={"session_id": session_id, "name": "To Clean"})
    collection_id = col_res.json()["id"]
    await client.post(f"/api/widgets/{widget.id}/save", json={
        "session_id": session_id,
        "display_name": "In Col",
        "collection_ids": [collection_id],
    })
    res = await client.delete(f"/api/widgets/{widget.id}/save", params={"session_id": session_id})
    assert res.status_code == 204
