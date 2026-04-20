import enum
import uuid

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DataSourceType(str, enum.Enum):
    POSTGRESQL = "POSTGRESQL"
    MYSQL = "MYSQL"
    SQLITE = "SQLITE"
    JSON = "JSON"


class ConnectionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    PENDING = "PENDING"


class DataSourceConnection(Base):
    """Representa una conexión configurada a una fuente de datos externa."""

    __tablename__ = "data_source_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[DataSourceType] = mapped_column(Enum(DataSourceType), nullable=False)
    connection_string: Mapped[str | None] = mapped_column(String, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus),
        nullable=False,
        default=ConnectionStatus.PENDING,
    )
