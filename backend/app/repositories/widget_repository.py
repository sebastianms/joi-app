from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.widget import WidgetORM, _utcnow


class WidgetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, widget_id: str, session_id: str) -> Optional[WidgetORM]:
        result = await self._db.execute(
            select(WidgetORM).where(
                WidgetORM.id == widget_id,
                WidgetORM.session_id == session_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_saved(self, session_id: str) -> list[WidgetORM]:
        result = await self._db.execute(
            select(WidgetORM).where(
                WidgetORM.session_id == session_id,
                WidgetORM.is_saved.is_(True),
            )
        )
        return list(result.scalars().all())

    async def mark_saved(
        self,
        widget: WidgetORM,
        display_name: str,
    ) -> WidgetORM:
        widget.is_saved = True
        widget.display_name = display_name
        widget.saved_at = _utcnow()
        await self._db.flush()
        await self._db.refresh(widget)
        return widget

    async def mark_unsaved(self, widget: WidgetORM) -> WidgetORM:
        widget.is_saved = False
        widget.display_name = None
        widget.saved_at = None
        await self._db.flush()
        await self._db.refresh(widget)
        return widget

    async def is_in_any_dashboard(self, widget_id: str) -> bool:
        from app.models.dashboard import DashboardItem

        result = await self._db.execute(
            select(DashboardItem).where(DashboardItem.widget_id == widget_id).limit(1)
        )
        return result.scalar_one_or_none() is not None
