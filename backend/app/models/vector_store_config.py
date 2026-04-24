import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VectorStoreProvider(str, Enum):
    QDRANT = "qdrant"
    CHROMA = "chroma"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    PGVECTOR = "pgvector"


# ── ORM ───────────────────────────────────────────────────────────────────────


class VectorStoreConfigORM(Base):
    __tablename__ = "vector_store_configs"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_vector_store_config_session"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    connection_params_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


# ── Pydantic ──────────────────────────────────────────────────────────────────


class VectorStoreConfig(BaseModel):
    id: Optional[str] = None
    session_id: str
    provider: VectorStoreProvider
    is_default: bool = False
    last_validated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_orm(cls, orm: VectorStoreConfigORM) -> "VectorStoreConfig":
        return cls(
            id=orm.id,
            session_id=orm.session_id,
            provider=VectorStoreProvider(orm.provider),
            is_default=orm.is_default,
            last_validated_at=orm.last_validated_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
