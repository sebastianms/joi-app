import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_session_repository import UserSessionRepository


@pytest.fixture
async def repo(db_session: AsyncSession) -> UserSessionRepository:
    return UserSessionRepository(db_session)


async def test_get_or_create_creates_new_session(repo: UserSessionRepository):
    session = await repo.get_or_create("session-abc")

    assert session.session_id == "session-abc"
    assert session.rag_enabled is True
    assert session.created_at is not None
    assert session.updated_at is not None


async def test_get_or_create_is_idempotent(repo: UserSessionRepository):
    first = await repo.get_or_create("session-xyz")
    second = await repo.get_or_create("session-xyz")

    assert first.session_id == second.session_id
    assert first.created_at == second.created_at


async def test_get_by_id_returns_none_for_unknown(repo: UserSessionRepository):
    result = await repo.get_by_id("does-not-exist")

    assert result is None


async def test_get_by_id_returns_existing_session(repo: UserSessionRepository):
    await repo.get_or_create("session-known")

    result = await repo.get_by_id("session-known")

    assert result is not None
    assert result.session_id == "session-known"


async def test_set_rag_enabled_updates_flag(repo: UserSessionRepository):
    await repo.get_or_create("session-rag")

    updated = await repo.set_rag_enabled("session-rag", False)

    assert updated.rag_enabled is False


async def test_set_rag_enabled_updates_updated_at(repo: UserSessionRepository):
    original = await repo.get_or_create("session-ts")
    original_updated_at = original.updated_at

    updated = await repo.set_rag_enabled("session-ts", False)

    assert updated.updated_at >= original_updated_at
