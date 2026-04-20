import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.connection import ConnectionStatus, DataSourceConnection, DataSourceType
from app.repositories.connection_repository import SQLiteConnectionRepository

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def repo(db_session: AsyncSession) -> SQLiteConnectionRepository:
    return SQLiteConnectionRepository(db_session)


def build_connection(
    session_id: str = "session-1",
    name: str = "Test DB",
    db_type: DataSourceType = DataSourceType.SQLITE,
    connection_string: str = "sqlite:///test.db",
) -> DataSourceConnection:
    return DataSourceConnection(
        user_session_id=session_id,
        name=name,
        source_type=db_type,
        connection_string=connection_string,
        status=ConnectionStatus.PENDING,
    )


async def test_save_persists_connection(repo: SQLiteConnectionRepository):
    connection = build_connection()

    saved = await repo.save(connection)

    assert saved.id is not None
    assert saved.name == "Test DB"
    assert saved.status == ConnectionStatus.PENDING


async def test_find_by_id_returns_saved_connection(repo: SQLiteConnectionRepository):
    connection = build_connection()
    saved = await repo.save(connection)

    found = await repo.find_by_id(saved.id)

    assert found is not None
    assert found.id == saved.id


async def test_find_by_id_returns_none_for_unknown_id(repo: SQLiteConnectionRepository):
    result = await repo.find_by_id("non-existent-id")

    assert result is None


async def test_find_by_session_returns_only_owned_connections(repo: SQLiteConnectionRepository):
    await repo.save(build_connection(session_id="session-A"))
    await repo.save(build_connection(session_id="session-A"))
    await repo.save(build_connection(session_id="session-B"))

    results = await repo.find_by_session("session-A")

    assert len(results) == 2
    assert all(c.user_session_id == "session-A" for c in results)
