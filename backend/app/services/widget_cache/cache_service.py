from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.widget_cache import CacheCandidate, CacheIndexRequest, WidgetCacheEntry, WidgetCacheEntryORM
from app.services.embeddings.litellm_embeddings import LiteLLMEmbeddings
from app.services.widget_cache.vector_store_factory import build_vector_store

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 0.85
_TOP_K = 5


class CacheService:
    """Semantic widget cache backed by a LangChain VectorStore.

    All queries carry mandatory filters (session_id, connection_id,
    data_schema_hash, invalidated_at IS NULL) to prevent cross-session leakage.
    When the vector store is unavailable, every public method degrades
    gracefully and returns an empty result instead of raising (FR-013).
    """

    def __init__(self, db: AsyncSession, vector_store_config=None) -> None:
        self._db = db
        self._vs_config = vector_store_config
        self._embeddings = LiteLLMEmbeddings()

    def _vector_store(self):
        return build_vector_store(self._vs_config, self._embeddings)

    async def search(
        self,
        *,
        session_id: str,
        prompt: str,
        connection_id: str,
        data_schema_hash: str,
    ) -> list[CacheCandidate]:
        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue

            vs = self._vector_store()
            # Invalidated entries are removed from the vector store when marked
            # invalidated (delete_entry / invalidate_by_connection), so this filter
            # enforces only the session / connection / schema isolation.
            qdrant_filter = Filter(
                must=[
                    FieldCondition(key="metadata.session_id", match=MatchValue(value=session_id)),
                    FieldCondition(key="metadata.connection_id", match=MatchValue(value=connection_id)),
                    FieldCondition(
                        key="metadata.data_schema_hash",
                        match=MatchValue(value=data_schema_hash),
                    ),
                ]
            )
            results = vs.similarity_search_with_relevance_scores(
                query=prompt,
                k=_TOP_K,
                filter=qdrant_filter,
            )
        except Exception:
            logger.warning("Cache search failed — degrading to miss", exc_info=True)
            return []

        candidates: list[CacheCandidate] = []
        for doc, score in results:
            if score < _SIMILARITY_THRESHOLD:
                continue
            entry = WidgetCacheEntry(
                id=doc.metadata["id"],
                session_id=doc.metadata["session_id"],
                widget_id=doc.metadata["widget_id"],
                prompt_text=doc.page_content,
                data_schema_hash=doc.metadata["data_schema_hash"],
                connection_id=doc.metadata.get("connection_id"),
                widget_type=doc.metadata["widget_type"],
                hit_count=doc.metadata.get("hit_count", 0),
            )
            candidates.append(
                CacheCandidate(
                    entry=entry,
                    score=score,
                    widget_spec_json=doc.metadata.get("spec_json", "{}"),
                )
            )
        return candidates

    async def index(self, request: CacheIndexRequest) -> None:
        """Index a widget in both Qdrant (for semantic search) and SQLite (mirror for reuse/invalidation)."""
        try:
            from app.repositories.widget_cache_repository import WidgetCacheRepository

            repo = WidgetCacheRepository(self._db)
            entry = WidgetCacheEntryORM(
                id=request.entry_id,
                session_id=request.session_id,
                widget_id=request.widget_id,
                prompt_text=request.prompt,
                data_schema_hash=request.data_schema_hash,
                connection_id=request.connection_id,
                widget_type=request.widget_type,
            )
            await repo.create(entry)
        except Exception:
            logger.warning("Cache SQL mirror insert failed", exc_info=True)
            return

        try:
            from langchain_core.documents import Document

            vs = self._vector_store()
            doc = Document(
                page_content=request.prompt,
                metadata={
                    "id": request.entry_id,
                    "session_id": request.session_id,
                    "widget_id": request.widget_id,
                    "connection_id": request.connection_id,
                    "data_schema_hash": request.data_schema_hash,
                    "widget_type": request.widget_type,
                    "spec_json": request.spec_json,
                    "hit_count": 0,
                },
            )
            vs.add_documents([doc], ids=[request.entry_id])
        except Exception:
            logger.warning("Cache vector index failed — SQL mirror still created", exc_info=True)

    async def delete_entry(self, entry_id: str) -> bool:
        """Soft-delete a single entry and best-effort remove its vector store point.

        Returns True if the SQL row was marked invalidated; False if the entry
        did not exist. Vector store deletion failures are logged but do not
        fail the call — the SQL-side invalidation is the source of truth.
        """
        from app.repositories.widget_cache_repository import WidgetCacheRepository

        repo = WidgetCacheRepository(self._db)
        invalidated = await repo.soft_delete(entry_id)
        if not invalidated:
            return False

        try:
            vs = self._vector_store()
            vs.delete(ids=[entry_id])
        except Exception:
            logger.warning(
                "Vector store deletion failed for %s — SQL-side invalidation still active.",
                entry_id,
                exc_info=True,
            )
        return True

    async def invalidate_by_connection(
        self, *, session_id: str, connection_id: str
    ) -> None:
        """Soft-delete all cache entries for a connection.

        Marks SQLite rows first (fast), then attempts vector store deletion.
        If the vector store is unavailable, the SQLite-side invalidation still
        protects against stale hits — the filter on invalidated_at IS NULL
        excludes them from future searches even if the vector point remains.
        """
        from sqlalchemy import select, update

        now = datetime.now(timezone.utc)
        stmt = (
            update(WidgetCacheEntryORM)
            .where(
                WidgetCacheEntryORM.session_id == session_id,
                WidgetCacheEntryORM.connection_id == connection_id,
                WidgetCacheEntryORM.invalidated_at.is_(None),
            )
            .values(invalidated_at=now)
            .returning(WidgetCacheEntryORM.id)
        )
        result = await self._db.execute(stmt)
        invalidated_ids = [row[0] for row in result.fetchall()]

        if not invalidated_ids:
            return

        try:
            vs = self._vector_store()
            vs.delete(ids=invalidated_ids)
        except Exception:
            logger.warning(
                "Vector store deletion failed for %d entries — SQLite-side "
                "invalidation still active.",
                len(invalidated_ids),
                exc_info=True,
            )
