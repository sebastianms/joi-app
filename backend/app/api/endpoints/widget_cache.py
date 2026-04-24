"""Widget cache endpoints (US5 — T092, T093, T094)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.widget_cache_repository import WidgetCacheRepository
from app.services.widget_cache.cache_service import CacheService

router = APIRouter()


class CacheSearchRequest(BaseModel):
    session_id: str
    prompt: str
    connection_id: str
    data_schema_hash: str


class CacheSearchResponse(BaseModel):
    candidates: list[dict]


class CacheReuseRequest(BaseModel):
    session_id: str


@router.post("/search", response_model=CacheSearchResponse, status_code=status.HTTP_200_OK)
async def search_cache(
    body: CacheSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> CacheSearchResponse:
    """Semantic search against the widget cache."""
    service = CacheService(db)
    candidates = await service.search(
        session_id=body.session_id,
        prompt=body.prompt,
        connection_id=body.connection_id,
        data_schema_hash=body.data_schema_hash,
    )
    return CacheSearchResponse(
        candidates=[
            {
                "cache_entry_id": c.entry.id,
                "score": c.score,
                "widget_type": c.entry.widget_type,
                "prompt_text": c.entry.prompt_text,
                "hit_count": c.entry.hit_count,
            }
            for c in candidates
        ]
    )


@router.post("/{entry_id}/reuse", status_code=status.HTTP_200_OK)
async def reuse_cache_entry(
    entry_id: str,
    body: CacheReuseRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Increment hit_count and last_used_at for a cache entry.

    The frontend already holds the widget_spec from the original cache_suggestion;
    this call only registers the reuse event.
    """
    repo = WidgetCacheRepository(db)
    entry = await repo.get(entry_id)
    if entry is None or entry.invalidated_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cache entry not found")
    if entry.session_id != body.session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session mismatch")

    await repo.increment_hit(entry_id)
    await db.commit()

    return {"cache_entry_id": entry_id, "widget_id": entry.widget_id, "hit_count": entry.hit_count}


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_cache_entry(
    entry_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a cache entry (and best-effort remove from the vector store)."""
    repo = WidgetCacheRepository(db)
    entry = await repo.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cache entry not found")
    if entry.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session mismatch")

    deleted = await CacheService(db).delete_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cache entry not found")

    await db.commit()
