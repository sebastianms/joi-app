from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "widget_cache"
_VECTOR_SIZE = 1536  # text-embedding-3-small output dimension


async def ensure_widget_cache_collection() -> None:
    """Create the Qdrant widget_cache collection if it does not exist.

    Called once during the FastAPI lifespan startup so the collection is ready
    before any request tries to index or search. Failures here are logged and
    swallowed — the pipeline degrades gracefully per FR-013.
    """
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import Distance, VectorParams

        client = QdrantClient(url=settings.QDRANT_URL, timeout=5)
        existing = {c.name for c in client.get_collections().collections}
        if _COLLECTION_NAME not in existing:
            client.create_collection(
                collection_name=_COLLECTION_NAME,
                vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection '%s'", _COLLECTION_NAME)
        else:
            logger.debug("Qdrant collection '%s' already exists", _COLLECTION_NAME)
    except Exception:
        logger.warning(
            "Could not connect to Qdrant at %s — widget cache disabled for this run.",
            settings.QDRANT_URL,
            exc_info=True,
        )
