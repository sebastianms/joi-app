from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.connection import DataSourceConnection, DataSourceType, ConnectionStatus
from app.repositories.connection_repository import SQLiteConnectionRepository
from app.services.connection_tester import ConnectionTesterService

router = APIRouter()


class ConnectionCreateRequest(BaseModel):
    user_session_id: str
    name: str
    connection_string: str
    source_type: DataSourceType

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_session_id": "session-123",
                "name": "Local SQLite",
                "connection_string": "sqlite+aiosqlite:////tmp/test.db",
                "source_type": "SQLITE"
            }
        }
    )


class ConnectionResponse(BaseModel):
    id: str
    user_session_id: str
    name: str
    source_type: DataSourceType
    status: ConnectionStatus

    model_config = ConfigDict(from_attributes=True)


@router.post("/sql", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_sql_connection(
    request: ConnectionCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Recibe una URI de conexión SQL, la prueba (ping) y si es válida la persiste.
    """
    # 1. Probar la conexión usando el servicio de dominio (SRP)
    tester = ConnectionTesterService()
    is_valid, error_msg = await tester.test_connection(request.connection_string)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection test failed: {error_msg}",
        )

    # 2. Si es válida, mapear al modelo de base de datos
    new_connection = DataSourceConnection(
        user_session_id=request.user_session_id,
        name=request.name,
        source_type=request.source_type,
        connection_string=request.connection_string,
        status=ConnectionStatus.ACTIVE,  # Se marca como ACTIVE porque acaba de pasar el test
    )

    # 3. Guardar en el repositorio (DIP)
    repo = SQLiteConnectionRepository(db)
    saved_connection = await repo.save(new_connection)

    return saved_connection
