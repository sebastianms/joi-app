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

    async def upsert_from_spec(self, spec, spec_json: str) -> WidgetORM:
        """Persist the widget row if it doesn't exist yet. Idempotent.

        Widgets are emitted by the architect and kept in-memory until saved.
        This ensures the row exists so POST /widgets/{id}/save can mutate it
        without 404ing. Called once per successful generation.
        """
        existing = await self._db.execute(
            select(WidgetORM).where(WidgetORM.id == spec.widget_id)
        )
        if existing.scalar_one_or_none() is not None:
            return existing.scalar_one()
        row = WidgetORM(
            id=spec.widget_id,
            session_id=spec.session_id,
            extraction_id=spec.extraction_id,
            widget_type=spec.widget_type.value,
            selection_source=spec.selection_source.value,
            render_mode=spec.render_mode.value,
            spec_json=spec_json,
        )
        self._db.add(row)
        await self._db.flush()
        return row

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
