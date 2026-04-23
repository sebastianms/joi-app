from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.render_mode import (
    RenderMode,
    RenderModeProfile,
    RenderModeProfileORM,
    UILibrary,
)


class RenderModeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, session_id: str) -> RenderModeProfile:
        orm = await self._get_orm(session_id)
        if orm is None:
            orm = RenderModeProfileORM(
                session_id=session_id,
                mode=RenderMode.UI_FRAMEWORK.value,
                ui_library=UILibrary.SHADCN.value,
            )
            self._session.add(orm)
            await self._session.commit()
            await self._session.refresh(orm)
        return RenderModeProfile.from_orm(orm)

    async def update(self, session_id: str, mode: RenderMode, ui_library: UILibrary | None) -> RenderModeProfile:
        orm = await self._get_orm(session_id)
        if orm is None:
            orm = RenderModeProfileORM(session_id=session_id)
            self._session.add(orm)
        orm.mode = mode.value
        orm.ui_library = ui_library.value if ui_library else None
        orm.updated_at = datetime.now(timezone.utc)
        await self._session.commit()
        await self._session.refresh(orm)
        return RenderModeProfile.from_orm(orm)

    async def _get_orm(self, session_id: str) -> RenderModeProfileORM | None:
        result = await self._session.execute(
            select(RenderModeProfileORM).where(
                RenderModeProfileORM.session_id == session_id
            )
        )
        return result.scalar_one_or_none()
