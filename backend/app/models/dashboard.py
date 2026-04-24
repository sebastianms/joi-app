import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Dashboard(Base):
    __tablename__ = "dashboards"
    __table_args__ = (
        UniqueConstraint("session_id", "name", name="uq_dashboard_name_per_session"),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class DashboardItem(Base):
    __tablename__ = "dashboard_items"
    __table_args__ = (
        UniqueConstraint(
            "dashboard_id", "widget_id", name="uq_dashboard_item_widget"
        ),
    )

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dashboard_id: Mapped[str] = mapped_column(
        String, ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    widget_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("widgets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    grid_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grid_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    z_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
