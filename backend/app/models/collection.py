import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (
        UniqueConstraint("session_id", "name", name="uq_collection_name_per_session"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class CollectionWidget(Base):
    """Junction table — widget can belong to multiple collections (N:M)."""

    __tablename__ = "collection_widgets"
    __table_args__ = (
        Index("ix_collection_widgets_widget_id", "widget_id"),
    )

    collection_id: Mapped[str] = mapped_column(
        String, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    widget_id: Mapped[str] = mapped_column(
        String, ForeignKey("widgets.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
