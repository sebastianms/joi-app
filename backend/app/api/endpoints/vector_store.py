"""BYO vector store endpoints (US5b — T100)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.vector_store_config import VectorStoreProvider
from app.repositories.vector_store_config_repository import VectorStoreConfigRepository
from app.services.widget_cache.vector_store_factory import validate_vector_store

router = APIRouter()


class VectorStoreValidateRequest(BaseModel):
    provider: VectorStoreProvider
    connection_params: dict[str, Any]


class VectorStoreConfigRequest(BaseModel):
    session_id: str
    provider: VectorStoreProvider
    connection_params: dict[str, Any]


class VectorStoreConfigResponse(BaseModel):
    id: str
    session_id: str
    provider: str
    is_default: bool
    last_validated_at: Optional[datetime]
    created_at: Optional[datetime]


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_config(body: VectorStoreValidateRequest) -> dict:
    """Attempt a ping/similarity search against the provided vector store config."""
    try:
        validate_vector_store(body.provider.value, body.connection_params)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return {"valid": True}


@router.post("/config", response_model=VectorStoreConfigResponse, status_code=status.HTTP_201_CREATED)
async def save_config(
    body: VectorStoreConfigRequest,
    db: AsyncSession = Depends(get_db),
) -> VectorStoreConfigResponse:
    """Persist BYO vector store credentials (encrypted at rest) for a session."""
    repo = VectorStoreConfigRepository(db)
    orm = await repo.upsert(
        session_id=body.session_id,
        provider=body.provider,
        connection_params=body.connection_params,
    )
    orm.last_validated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(orm)
    return VectorStoreConfigResponse(
        id=orm.id,
        session_id=orm.session_id,
        provider=orm.provider,
        is_default=orm.is_default,
        last_validated_at=orm.last_validated_at,
        created_at=orm.created_at,
    )


@router.get("/config", response_model=Optional[VectorStoreConfigResponse], status_code=status.HTTP_200_OK)
async def get_config(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> Optional[VectorStoreConfigResponse]:
    """Return the current vector store config for a session (without credentials)."""
    repo = VectorStoreConfigRepository(db)
    orm = await repo.get_by_session(session_id)
    if orm is None:
        return None
    return VectorStoreConfigResponse(
        id=orm.id,
        session_id=orm.session_id,
        provider=orm.provider,
        is_default=orm.is_default,
        last_validated_at=orm.last_validated_at,
        created_at=orm.created_at,
    )


@router.delete("/config", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_config(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove BYO config — session falls back to the default Qdrant instance."""
    repo = VectorStoreConfigRepository(db)
    deleted = await repo.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    await db.commit()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return provider + reachability for the active vector store of a session."""
    repo = VectorStoreConfigRepository(db)
    orm = await repo.get_by_session(session_id)

    if orm is None or orm.is_default:
        provider = "qdrant"
        is_default = True
    else:
        provider = orm.provider
        is_default = False

    try:
        from app.services.widget_cache.bootstrap import _ping_qdrant  # type: ignore[attr-defined]
        if is_default:
            from app.core.config import settings
            from qdrant_client import QdrantClient
            client = QdrantClient(url=settings.QDRANT_URL)
            client.get_collections()
            healthy = True
        else:
            params = await repo.get_decrypted_params(session_id) or {}
            validate_vector_store(provider, params)
            healthy = True
    except Exception:
        healthy = False

    return {"provider": provider, "is_default": is_default, "healthy": healthy}
