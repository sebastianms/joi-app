from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
import app.models.user_session  # noqa: F401 — registra UserSession en Base.metadata
import app.models.render_mode  # noqa: F401 — registra RenderModeProfileORM en Base.metadata

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar las tablas de base de datos
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
