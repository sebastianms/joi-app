import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── ORM ───────────────────────────────────────────────────────────────────────


class WidgetCacheEntryORM(Base):
    """SQLite metadata mirror for the vector store entry. The embedding lives in
    the provider (Qdrant by default). This table enables fast SQL invalidation
    and analytics without querying the vector store."""

    __tablename__ = "widget_cache_entries"
    __table_args__ = (
        Index("ix_cache_session_invalidated", "session_id", "invalidated_at"),
        Index("ix_cache_connection_id", "connection_id"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("user_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    widget_id: Mapped[str] = mapped_column(
        String, ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False
    )
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    data_schema_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    connection_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("data_source_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    widget_type: Mapped[str] = mapped_column(String(32), nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


# ── Pydantic ──────────────────────────────────────────────────────────────────


class WidgetCacheEntry(BaseModel):
    id: str
    session_id: str
    widget_id: str
    prompt_text: str
    data_schema_hash: str
    connection_id: Optional[str]
    widget_type: str
    hit_count: int = 0
    last_used_at: Optional[datetime] = None
    invalidated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_orm(cls, orm: WidgetCacheEntryORM) -> "WidgetCacheEntry":
        return cls(
            id=orm.id,
            session_id=orm.session_id,
            widget_id=orm.widget_id,
            prompt_text=orm.prompt_text,
            data_schema_hash=orm.data_schema_hash,
            connection_id=orm.connection_id,
            widget_type=orm.widget_type,
            hit_count=orm.hit_count,
            last_used_at=orm.last_used_at,
            invalidated_at=orm.invalidated_at,
            created_at=orm.created_at,
        )


class CacheCandidate(BaseModel):
    """Result returned by CacheService.search — a scored cache hit."""

    entry: WidgetCacheEntry
    score: float
    widget_spec_json: str
