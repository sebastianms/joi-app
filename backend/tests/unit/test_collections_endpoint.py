import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSession


@pytest.fixture
async def session_id(db_session: AsyncSession) -> str:
    s = UserSession(session_id="sess-col-ep-1")
    db_session.add(s)
    await db_session.flush()
    return s.session_id


async def test_create_collection_returns_201(client: AsyncClient, session_id: str):
    res = await client.post("/api/collections", json={"session_id": session_id, "name": "Charts"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Charts"
    assert data["session_id"] == session_id


async def test_create_duplicate_name_returns_409(client: AsyncClient, session_id: str):
    await client.post("/api/collections", json={"session_id": session_id, "name": "Charts"})
    res = await client.post("/api/collections", json={"session_id": session_id, "name": "Charts"})
    assert res.status_code == 409


async def test_list_collections_empty(client: AsyncClient, session_id: str):
    res = await client.get("/api/collections", params={"session_id": session_id})
    assert res.status_code == 200
    assert res.json() == []


async def test_list_collections_returns_created(client: AsyncClient, session_id: str):
    await client.post("/api/collections", json={"session_id": session_id, "name": "KPIs"})
    await client.post("/api/collections", json={"session_id": session_id, "name": "Tables"})
    res = await client.get("/api/collections", params={"session_id": session_id})
    assert res.status_code == 200
    names = {c["name"] for c in res.json()}
    assert names == {"KPIs", "Tables"}


async def test_list_collections_session_isolation(client: AsyncClient, db_session: AsyncSession):
    s2 = UserSession(session_id="sess-col-ep-2")
    db_session.add(s2)
    await db_session.flush()

    await client.post("/api/collections", json={"session_id": "sess-col-ep-1", "name": "Col A"})
    await client.post("/api/collections", json={"session_id": "sess-col-ep-2", "name": "Col B"})

    res = await client.get("/api/collections", params={"session_id": "sess-col-ep-2"})
    names = [c["name"] for c in res.json()]
    assert names == ["Col B"]
