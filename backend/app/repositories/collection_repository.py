from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection import Collection, CollectionWidget


class CollectionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_by_session(self, session_id: str) -> list[Collection]:
        result = await self._db.execute(
            select(Collection).where(Collection.session_id == session_id)
        )
        return list(result.scalars().all())

    async def get(self, collection_id: str, session_id: str) -> Optional[Collection]:
        result = await self._db.execute(
            select(Collection).where(
                Collection.id == collection_id,
                Collection.session_id == session_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, session_id: str, name: str) -> Collection:
        collection = Collection(session_id=session_id, name=name)
        self._db.add(collection)
        await self._db.flush()
        await self._db.refresh(collection)
        return collection

    async def update_name(self, collection_id: str, session_id: str, name: str) -> Optional[Collection]:
        collection = await self.get(collection_id, session_id)
        if collection is None:
            return None
        collection.name = name
        await self._db.flush()
        return collection

    async def delete(self, collection_id: str, session_id: str) -> bool:
        collection = await self.get(collection_id, session_id)
        if collection is None:
            return False
        await self._db.delete(collection)
        await self._db.flush()
        return True

    async def add_widget(self, collection_id: str, widget_id: str) -> None:
        existing = await self._db.execute(
            select(CollectionWidget).where(
                CollectionWidget.collection_id == collection_id,
                CollectionWidget.widget_id == widget_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            self._db.add(CollectionWidget(collection_id=collection_id, widget_id=widget_id))
            await self._db.flush()

    async def remove_widget(self, collection_id: str, widget_id: str) -> None:
        await self._db.execute(
            delete(CollectionWidget).where(
                CollectionWidget.collection_id == collection_id,
                CollectionWidget.widget_id == widget_id,
            )
        )
        await self._db.flush()

    async def list_widget_ids(self, collection_id: str) -> list[str]:
        result = await self._db.execute(
            select(CollectionWidget.widget_id).where(
                CollectionWidget.collection_id == collection_id
            )
        )
        return list(result.scalars().all())

    async def collection_ids_for_widget(self, widget_id: str) -> list[str]:
        result = await self._db.execute(
            select(CollectionWidget.collection_id).where(
                CollectionWidget.widget_id == widget_id
            )
        )
        return list(result.scalars().all())
