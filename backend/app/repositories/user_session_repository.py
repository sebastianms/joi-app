from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSession


class UserSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, session_id: str) -> UserSession:
        existing = await self.get_by_id(session_id)
        if existing is not None:
            return existing
        user_session = UserSession(session_id=session_id)
        self._session.add(user_session)
        await self._session.commit()
        await self._session.refresh(user_session)
        return user_session

    async def get_by_id(self, session_id: str) -> UserSession | None:
        result = await self._session.execute(
            select(UserSession).where(UserSession.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def set_rag_enabled(self, session_id: str, enabled: bool) -> UserSession:
        user_session = await self.get_or_create(session_id)
        user_session.rag_enabled = enabled
        user_session.updated_at = datetime.now(timezone.utc)
        await self._session.commit()
        await self._session.refresh(user_session)
        return user_session
