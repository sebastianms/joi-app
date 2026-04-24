from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base  # noqa: F401 — re-exportado para que Alembic lo detecte

engine = create_async_engine(settings.DATABASE_URL, echo=False)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency que provee una sesión de base de datos por request.

    Commits on successful exit so endpoints don't need to call `db.commit()`
    explicitly after every write. Rolls back on exception so partial state is
    never persisted.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
