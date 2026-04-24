from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vector_store_config import VectorStoreConfigORM, VectorStoreProvider
from app.services.security.encryption import decrypt, encrypt


class VectorStoreConfigRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_session(self, session_id: str) -> Optional[VectorStoreConfigORM]:
        result = await self._db.execute(
            select(VectorStoreConfigORM).where(
                VectorStoreConfigORM.session_id == session_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        session_id: str,
        provider: VectorStoreProvider,
        connection_params: dict,
        *,
        is_default: bool = False,
    ) -> VectorStoreConfigORM:
        """Create or replace the vector store config for a session.

        connection_params are encrypted before storage so credentials never
        appear in plaintext in the database (SEC-001).
        """
        encrypted = encrypt(json.dumps(connection_params))
        existing = await self.get_by_session(session_id)
        if existing is not None:
            existing.provider = provider.value
            existing.connection_params_encrypted = encrypted
            existing.is_default = is_default
            await self._db.flush()
            return existing

        config = VectorStoreConfigORM(
            session_id=session_id,
            provider=provider.value,
            connection_params_encrypted=encrypted,
            is_default=is_default,
        )
        self._db.add(config)
        await self._db.flush()
        await self._db.refresh(config)
        return config

    async def get_decrypted_params(self, session_id: str) -> Optional[dict]:
        config = await self.get_by_session(session_id)
        if config is None:
            return None
        return json.loads(decrypt(config.connection_params_encrypted))

    async def delete(self, session_id: str) -> bool:
        config = await self.get_by_session(session_id)
        if config is None:
            return False
        await self._db.delete(config)
        await self._db.flush()
        return True
