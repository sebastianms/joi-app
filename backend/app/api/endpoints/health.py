"""Global health endpoint (US5 Polish — T200)."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.config import settings

router = APIRouter()


def _default_qdrant_healthy() -> bool:
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=settings.QDRANT_URL, timeout=2)
        client.get_collections()
        return True
    except Exception:
        return False


@router.get("", status_code=status.HTTP_200_OK)
async def health() -> dict:
    """Global health with sub-status for the default vector store."""
    return {
        "status": "ok",
        "vector_store": {
            "provider": "qdrant",
            "is_default": True,
            "healthy": _default_qdrant_healthy(),
        },
    }
