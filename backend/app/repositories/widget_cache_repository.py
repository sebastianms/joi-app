from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.widget_cache import WidgetCacheEntryORM


class WidgetCacheRepository:
    """Manages SQLite metadata for widget cache entries.

    This repository only touches the relational metadata side. The vector
    store (embeddings) is managed separately via CacheService.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, entry: WidgetCacheEntryORM) -> WidgetCacheEntryORM:
        self._db.add(entry)
        await self._db.flush()
        return entry

    async def get(self, entry_id: str) -> Optional[WidgetCacheEntryORM]:
        result = await self._db.execute(
            select(WidgetCacheEntryORM).where(WidgetCacheEntryORM.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def increment_hit(self, entry_id: str) -> None:
        entry = await self.get(entry_id)
        if entry is None:
            return
        entry.hit_count += 1
        entry.last_used_at = datetime.now(timezone.utc)
        await self._db.flush()

    async def soft_delete(self, entry_id: str) -> bool:
        entry = await self.get(entry_id)
        if entry is None:
            return False
        entry.invalidated_at = datetime.now(timezone.utc)
        await self._db.flush()
        return True

    async def invalidate_by_connection(
        self, session_id: str, connection_id: str
    ) -> list[str]:
        """Soft-delete all active entries for a connection. Returns invalidated IDs."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(WidgetCacheEntryORM)
            .where(
                WidgetCacheEntryORM.session_id == session_id,
                WidgetCacheEntryORM.connection_id == connection_id,
                WidgetCacheEntryORM.invalidated_at.is_(None),
            )
            .values(invalidated_at=now)
            .returning(WidgetCacheEntryORM.id)
        )
        result = await self._db.execute(stmt)
        return [row[0] for row in result.fetchall()]
