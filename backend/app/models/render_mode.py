import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, model_validator
from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RenderMode(str, Enum):
    UI_FRAMEWORK = "ui_framework"
    FREE_CODE = "free_code"
    DESIGN_SYSTEM = "design_system"


class UILibrary(str, Enum):
    SHADCN = "shadcn"
    BOOTSTRAP = "bootstrap"
    HEROUI = "heroui"


# ── ORM ───────────────────────────────────────────────────────────────────────


class RenderModeProfileORM(Base):
    __tablename__ = "render_mode_profiles"
    __table_args__ = (UniqueConstraint("session_id", name="uq_render_mode_session"),)

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String, nullable=False, default="ui_framework")
    ui_library: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="shadcn")
    design_system_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


# ── Pydantic ──────────────────────────────────────────────────────────────────


class RenderModeProfile(BaseModel):
    id: Optional[str] = None
    session_id: str
    mode: RenderMode = RenderMode.UI_FRAMEWORK
    ui_library: Optional[UILibrary] = UILibrary.SHADCN
    design_system_ref: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_mode_constraints(self) -> "RenderModeProfile":
        if self.mode == RenderMode.DESIGN_SYSTEM:
            raise ValueError("design_system mode is deferred post-MVP and cannot be set")
        if self.mode == RenderMode.UI_FRAMEWORK and self.ui_library is None:
            raise ValueError("ui_library is required when mode=ui_framework")
        if self.mode == RenderMode.FREE_CODE:
            self.ui_library = None
        return self

    @classmethod
    def from_orm(cls, orm: RenderModeProfileORM) -> "RenderModeProfile":
        return cls(
            id=orm.id,
            session_id=orm.session_id,
            mode=RenderMode(orm.mode),
            ui_library=UILibrary(orm.ui_library) if orm.ui_library else None,
            design_system_ref=orm.design_system_ref,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )


class RenderModeProfileRef(BaseModel):
    """Lightweight reference serialized in ChatResponse (no timestamps)."""

    session_id: str
    mode: RenderMode
    ui_library: Optional[UILibrary] = None

    @classmethod
    def from_profile(cls, profile: RenderModeProfile) -> "RenderModeProfileRef":
        return cls(
            session_id=profile.session_id,
            mode=profile.mode,
            ui_library=profile.ui_library,
        )


class RenderModeUpdateRequest(BaseModel):
    mode: Literal["ui_framework", "free_code"]
    ui_library: Optional[Literal["shadcn", "bootstrap", "heroui"]] = None

    @model_validator(mode="after")
    def validate_library_required(self) -> "RenderModeUpdateRequest":
        if self.mode == "ui_framework" and self.ui_library is None:
            raise ValueError("ui_library is required when mode=ui_framework")
        return self
