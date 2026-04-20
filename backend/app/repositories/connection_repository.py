from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import DataSourceConnection
from app.repositories.base import DataSourceRepository


class SQLiteConnectionRepository(DataSourceRepository):
    """Implementación concreta de DataSourceRepository usando SQLAlchemy + SQLite."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, connection: DataSourceConnection) -> DataSourceConnection:
        self._session.add(connection)
        await self._session.commit()
        await self._session.refresh(connection)
        return connection

    async def find_by_id(self, connection_id: str) -> DataSourceConnection | None:
        result = await self._session.execute(
            select(DataSourceConnection).where(DataSourceConnection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def find_by_session(self, session_id: str) -> list[DataSourceConnection]:
        result = await self._session.execute(
            select(DataSourceConnection).where(
                DataSourceConnection.user_session_id == session_id
            )
        )
        return list(result.scalars().all())
