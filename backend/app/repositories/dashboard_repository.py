from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard import Dashboard, DashboardItem


class DashboardRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_by_session(self, session_id: str) -> list[Dashboard]:
        result = await self._db.execute(
            select(Dashboard).where(Dashboard.session_id == session_id)
        )
        return list(result.scalars().all())

    async def get(self, dashboard_id: str, session_id: str) -> Optional[Dashboard]:
        result = await self._db.execute(
            select(Dashboard).where(
                Dashboard.id == dashboard_id,
                Dashboard.session_id == session_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, session_id: str, name: str) -> Dashboard:
        dashboard = Dashboard(session_id=session_id, name=name)
        self._db.add(dashboard)
        await self._db.flush()
        await self._db.refresh(dashboard)
        return dashboard

    async def update_name(self, dashboard_id: str, session_id: str, name: str) -> Optional[Dashboard]:
        dashboard = await self.get(dashboard_id, session_id)
        if dashboard is None:
            return None
        dashboard.name = name
        await self._db.flush()
        return dashboard

    async def delete(self, dashboard_id: str, session_id: str) -> bool:
        dashboard = await self.get(dashboard_id, session_id)
        if dashboard is None:
            return False
        await self._db.delete(dashboard)
        await self._db.flush()
        return True

    async def list_items(self, dashboard_id: str) -> list[DashboardItem]:
        result = await self._db.execute(
            select(DashboardItem).where(DashboardItem.dashboard_id == dashboard_id)
        )
        return list(result.scalars().all())

    async def add_item(
        self,
        dashboard_id: str,
        widget_id: str,
        *,
        grid_x: int = 0,
        grid_y: int = 0,
        width: int = 4,
        height: int = 3,
    ) -> DashboardItem:
        item = DashboardItem(
            dashboard_id=dashboard_id,
            widget_id=widget_id,
            grid_x=grid_x,
            grid_y=grid_y,
            width=width,
            height=height,
        )
        self._db.add(item)
        await self._db.flush()
        await self._db.refresh(item)
        return item

    async def remove_item(self, dashboard_id: str, widget_id: str) -> None:
        await self._db.execute(
            delete(DashboardItem).where(
                DashboardItem.dashboard_id == dashboard_id,
                DashboardItem.widget_id == widget_id,
            )
        )
        await self._db.flush()

    async def update_layout(self, dashboard_id: str, items: list[dict]) -> None:
        """Replace the layout of all items in one shot.

        Each item dict must contain widget_id, grid_x, grid_y, width, height.
        Width is clamped to [1, 12] per the spec contract.
        """
        for item_data in items:
            result = await self._db.execute(
                select(DashboardItem).where(
                    DashboardItem.dashboard_id == dashboard_id,
                    DashboardItem.widget_id == item_data["widget_id"],
                )
            )
            item = result.scalar_one_or_none()
            if item is None:
                continue
            item.grid_x = item_data.get("grid_x", item.grid_x)
            item.grid_y = item_data.get("grid_y", item.grid_y)
            item.width = max(1, min(12, item_data.get("width", item.width)))
            item.height = max(1, item_data.get("height", item.height))
            item.z_order = item_data.get("z_order", item.z_order)
        await self._db.flush()
