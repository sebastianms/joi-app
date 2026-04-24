"""Unit tests for VectorStoreConfigRepository."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vector_store_config import VectorStoreProvider
from app.repositories.vector_store_config_repository import VectorStoreConfigRepository


async def test_upsert_creates_new_config(db_session: AsyncSession):
    repo = VectorStoreConfigRepository(db_session)
    config = await repo.upsert(
        session_id="s1",
        provider=VectorStoreProvider.QDRANT,
        connection_params={"url": "http://x:6333"},
    )
    assert config.session_id == "s1"
    assert config.provider == "qdrant"


async def test_upsert_replaces_existing(db_session: AsyncSession):
    repo = VectorStoreConfigRepository(db_session)
    await repo.upsert(
        session_id="s2",
        provider=VectorStoreProvider.QDRANT,
        connection_params={"url": "http://x:6333"},
    )
    updated = await repo.upsert(
        session_id="s2",
        provider=VectorStoreProvider.CHROMA,
        connection_params={"host": "localhost", "port": "8000"},
    )
    assert updated.provider == "chroma"


async def test_get_by_session_returns_none_when_absent(db_session: AsyncSession):
    repo = VectorStoreConfigRepository(db_session)
    result = await repo.get_by_session("ghost")
    assert result is None


async def test_get_decrypted_params_roundtrip(db_session: AsyncSession):
    repo = VectorStoreConfigRepository(db_session)
    await repo.upsert(
        session_id="s3",
        provider=VectorStoreProvider.PINECONE,
        connection_params={"api_key": "secret", "index_name": "x"},
    )
    params = await repo.get_decrypted_params("s3")
    assert params == {"api_key": "secret", "index_name": "x"}


async def test_get_decrypted_params_none_when_absent(db_session: AsyncSession):
    repo = VectorStoreConfigRepository(db_session)
    assert await repo.get_decrypted_params("ghost") is None


async def test_delete_removes_config(db_session: AsyncSession):
    repo = VectorStoreConfigRepository(db_session)
    await repo.upsert(
        session_id="s-del",
        provider=VectorStoreProvider.QDRANT,
        connection_params={"url": "http://x:6333"},
    )
    assert await repo.delete("s-del") is True
    assert await repo.get_by_session("s-del") is None


async def test_delete_returns_false_when_absent(db_session: AsyncSession):
    repo = VectorStoreConfigRepository(db_session)
    assert await repo.delete("never-existed") is False
