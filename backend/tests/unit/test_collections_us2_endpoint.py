import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection import Collection
from app.models.user_session import UserSession
from app.models.widget import WidgetORM


@pytest.fixture
async def session_id(db_session: AsyncSession) -> str:
    s = UserSession(session_id="sess-col-us2-1")
    db_session.add(s)
    await db_session.flush()
    return s.session_id


@pytest.fixture
async def collection(db_session: AsyncSession, session_id: str) -> Collection:
    col = Collection(session_id=session_id, name="Original")
    db_session.add(col)
    await db_session.flush()
    await db_session.refresh(col)
    return col


@pytest.fixture
async def saved_widget(db_session: AsyncSession, session_id: str) -> WidgetORM:
    w = WidgetORM(
        id="w-us2-1",
        session_id=session_id,
        extraction_id="ext-us2",
        widget_type="table",
        selection_source="deterministic",
        render_mode="ui_framework",
        spec_json="{}",
        is_saved=True,
        display_name="Revenue Chart",
    )
    db_session.add(w)
    await db_session.flush()
    return w


async def test_rename_collection_returns_200(client: AsyncClient, collection: Collection, session_id: str):
    res = await client.patch(
        f"/api/collections/{collection.id}",
        json={"session_id": session_id, "name": "Renamed"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed"


async def test_rename_collection_duplicate_returns_409(
    client: AsyncClient, collection: Collection, session_id: str
):
    await client.post("/api/collections", json={"session_id": session_id, "name": "Other"})
    res = await client.patch(
        f"/api/collections/{collection.id}",
        json={"session_id": session_id, "name": "Other"},
    )
    assert res.status_code == 409


async def test_rename_collection_not_found_returns_404(client: AsyncClient, session_id: str):
    res = await client.patch(
        "/api/collections/nonexistent",
        json={"session_id": session_id, "name": "X"},
    )
    assert res.status_code == 404


async def test_delete_collection_returns_204(client: AsyncClient, collection: Collection, session_id: str):
    res = await client.delete(f"/api/collections/{collection.id}", params={"session_id": session_id})
    assert res.status_code == 204


async def test_delete_collection_not_found_returns_404(client: AsyncClient, session_id: str):
    res = await client.delete("/api/collections/nonexistent", params={"session_id": session_id})
    assert res.status_code == 404


async def test_list_collection_widgets_empty(client: AsyncClient, collection: Collection, session_id: str):
    res = await client.get(
        f"/api/collections/{collection.id}/widgets",
        params={"session_id": session_id},
    )
    assert res.status_code == 200
    assert res.json() == []


async def test_list_collection_widgets_not_found_returns_404(client: AsyncClient, session_id: str):
    res = await client.get(
        "/api/collections/nonexistent/widgets",
        params={"session_id": session_id},
    )
    assert res.status_code == 404


async def test_list_collection_widgets_returns_saved_widgets(
    client: AsyncClient, collection: Collection, saved_widget: WidgetORM, session_id: str
):
    await client.post(
        f"/api/collections/{collection.id}/widgets",
        json={"session_id": session_id, "widget_ids": [saved_widget.id]},
    )
    res = await client.get(
        f"/api/collections/{collection.id}/widgets",
        params={"session_id": session_id},
    )
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["display_name"] == "Revenue Chart"


async def test_bulk_add_widgets_returns_204(
    client: AsyncClient, collection: Collection, saved_widget: WidgetORM, session_id: str
):
    res = await client.post(
        f"/api/collections/{collection.id}/widgets",
        json={"session_id": session_id, "widget_ids": [saved_widget.id]},
    )
    assert res.status_code == 204


async def test_bulk_add_widgets_collection_not_found_returns_404(
    client: AsyncClient, saved_widget: WidgetORM, session_id: str
):
    res = await client.post(
        "/api/collections/nonexistent/widgets",
        json={"session_id": session_id, "widget_ids": [saved_widget.id]},
    )
    assert res.status_code == 404


async def test_remove_widget_from_collection_returns_204(
    client: AsyncClient, collection: Collection, saved_widget: WidgetORM, session_id: str
):
    await client.post(
        f"/api/collections/{collection.id}/widgets",
        json={"session_id": session_id, "widget_ids": [saved_widget.id]},
    )
    res = await client.delete(
        f"/api/collections/{collection.id}/widgets/{saved_widget.id}",
        params={"session_id": session_id},
    )
    assert res.status_code == 204


async def test_remove_widget_collection_not_found_returns_404(
    client: AsyncClient, saved_widget: WidgetORM, session_id: str
):
    res = await client.delete(
        f"/api/collections/nonexistent/widgets/{saved_widget.id}",
        params={"session_id": session_id},
    )
    assert res.status_code == 404
