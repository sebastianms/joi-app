import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard import Dashboard
from app.models.user_session import UserSession
from app.models.widget import WidgetORM


@pytest.fixture
async def session_id(db_session: AsyncSession) -> str:
    s = UserSession(session_id="sess-dash-1")
    db_session.add(s)
    await db_session.flush()
    return s.session_id


@pytest.fixture
async def dashboard(db_session: AsyncSession, session_id: str) -> Dashboard:
    d = Dashboard(session_id=session_id, name="My Dashboard")
    db_session.add(d)
    await db_session.flush()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def saved_widget(db_session: AsyncSession, session_id: str) -> WidgetORM:
    w = WidgetORM(
        id="w-dash-1",
        session_id=session_id,
        extraction_id="ext-dash",
        widget_type="table",
        selection_source="deterministic",
        render_mode="ui_framework",
        spec_json="{}",
        is_saved=True,
        display_name="Sales Chart",
    )
    db_session.add(w)
    await db_session.flush()
    return w


async def test_create_dashboard_returns_201(client: AsyncClient, session_id: str):
    res = await client.post("/api/dashboards", json={"session_id": session_id, "name": "Q1"})
    assert res.status_code == 201
    assert res.json()["name"] == "Q1"


async def test_create_dashboard_duplicate_returns_409(
    client: AsyncClient, dashboard: Dashboard, session_id: str
):
    res = await client.post(
        "/api/dashboards", json={"session_id": session_id, "name": dashboard.name}
    )
    assert res.status_code == 409


async def test_list_dashboards_returns_created(client: AsyncClient, dashboard: Dashboard, session_id: str):
    res = await client.get("/api/dashboards", params={"session_id": session_id})
    assert res.status_code == 200
    assert any(d["id"] == dashboard.id for d in res.json())


async def test_get_dashboard_returns_items(
    client: AsyncClient, dashboard: Dashboard, saved_widget: WidgetORM, session_id: str
):
    await client.post(
        f"/api/dashboards/{dashboard.id}/items",
        json={"session_id": session_id, "widget_id": saved_widget.id},
    )
    res = await client.get(f"/api/dashboards/{dashboard.id}", params={"session_id": session_id})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == dashboard.id
    assert len(data["items"]) == 1
    assert data["items"][0]["display_name"] == "Sales Chart"


async def test_get_dashboard_not_found_returns_404(client: AsyncClient, session_id: str):
    res = await client.get("/api/dashboards/nonexistent", params={"session_id": session_id})
    assert res.status_code == 404


async def test_rename_dashboard_returns_200(
    client: AsyncClient, dashboard: Dashboard, session_id: str
):
    res = await client.patch(
        f"/api/dashboards/{dashboard.id}",
        json={"session_id": session_id, "name": "Renamed"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed"


async def test_rename_dashboard_not_found_returns_404(client: AsyncClient, session_id: str):
    res = await client.patch(
        "/api/dashboards/nonexistent", json={"session_id": session_id, "name": "X"}
    )
    assert res.status_code == 404


async def test_delete_dashboard_returns_204(
    client: AsyncClient, dashboard: Dashboard, session_id: str
):
    res = await client.delete(f"/api/dashboards/{dashboard.id}", params={"session_id": session_id})
    assert res.status_code == 204


async def test_delete_dashboard_not_found_returns_404(client: AsyncClient, session_id: str):
    res = await client.delete("/api/dashboards/nonexistent", params={"session_id": session_id})
    assert res.status_code == 404


async def test_add_item_returns_201(
    client: AsyncClient, dashboard: Dashboard, saved_widget: WidgetORM, session_id: str
):
    res = await client.post(
        f"/api/dashboards/{dashboard.id}/items",
        json={"session_id": session_id, "widget_id": saved_widget.id, "width": 6, "height": 3},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["widget_id"] == saved_widget.id
    assert data["display_name"] == "Sales Chart"
    assert data["width"] == 6


async def test_add_item_duplicate_returns_409(
    client: AsyncClient, dashboard: Dashboard, saved_widget: WidgetORM, session_id: str
):
    await client.post(
        f"/api/dashboards/{dashboard.id}/items",
        json={"session_id": session_id, "widget_id": saved_widget.id},
    )
    res = await client.post(
        f"/api/dashboards/{dashboard.id}/items",
        json={"session_id": session_id, "widget_id": saved_widget.id},
    )
    assert res.status_code == 409


async def test_add_item_dashboard_not_found_returns_404(
    client: AsyncClient, saved_widget: WidgetORM, session_id: str
):
    res = await client.post(
        "/api/dashboards/nonexistent/items",
        json={"session_id": session_id, "widget_id": saved_widget.id},
    )
    assert res.status_code == 404


async def test_add_item_widget_not_found_returns_404(
    client: AsyncClient, dashboard: Dashboard, session_id: str
):
    res = await client.post(
        f"/api/dashboards/{dashboard.id}/items",
        json={"session_id": session_id, "widget_id": "nonexistent"},
    )
    assert res.status_code == 404


async def test_remove_item_returns_204(
    client: AsyncClient, dashboard: Dashboard, saved_widget: WidgetORM, session_id: str
):
    await client.post(
        f"/api/dashboards/{dashboard.id}/items",
        json={"session_id": session_id, "widget_id": saved_widget.id},
    )
    res = await client.delete(
        f"/api/dashboards/{dashboard.id}/items/{saved_widget.id}",
        params={"session_id": session_id},
    )
    assert res.status_code == 204


async def test_remove_item_dashboard_not_found_returns_404(
    client: AsyncClient, saved_widget: WidgetORM, session_id: str
):
    res = await client.delete(
        f"/api/dashboards/nonexistent/items/{saved_widget.id}",
        params={"session_id": session_id},
    )
    assert res.status_code == 404


async def test_update_layout_returns_204(
    client: AsyncClient, dashboard: Dashboard, saved_widget: WidgetORM, session_id: str
):
    await client.post(
        f"/api/dashboards/{dashboard.id}/items",
        json={"session_id": session_id, "widget_id": saved_widget.id},
    )
    res = await client.patch(
        f"/api/dashboards/{dashboard.id}/layout",
        json={
            "session_id": session_id,
            "items": [{"widget_id": saved_widget.id, "grid_x": 2, "grid_y": 1, "width": 8, "height": 4}],
        },
    )
    assert res.status_code == 204


async def test_update_layout_dashboard_not_found_returns_404(
    client: AsyncClient, session_id: str
):
    res = await client.patch(
        "/api/dashboards/nonexistent/layout",
        json={"session_id": session_id, "items": []},
    )
    assert res.status_code == 404
