from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.services.widget_cache.bootstrap import ensure_widget_cache_collection
import app.models.user_session  # noqa: F401
import app.models.render_mode  # noqa: F401
import app.models.widget  # noqa: F401
import app.models.collection  # noqa: F401
import app.models.dashboard  # noqa: F401
import app.models.vector_store_config  # noqa: F401
import app.models.widget_cache  # noqa: F401


async def _init_db() -> None:
    if settings.DATABASE_URL.startswith("postgresql"):
        # Production: run pending Alembic migrations
        import asyncio
        from alembic.config import Config
        from alembic import command

        def _run(cfg: Config) -> None:
            command.upgrade(cfg, "head")

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        await asyncio.get_event_loop().run_in_executor(None, _run, alembic_cfg)
    else:
        # Development: create tables directly (SQLite, fast startup)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _init_db()
    await ensure_widget_cache_collection()
    yield

app = FastAPI(
    title="Joi-App API",
    description="Backend de la plataforma Joi-App — Generación Dinámica de UI con IA",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
