from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.connection import DataSourceConnection, DataSourceType, ConnectionStatus
from app.repositories.connection_repository import SQLiteConnectionRepository
from app.services.connection_tester import ConnectionTesterService
from app.services.json_handler import JsonFileService, FileTooLargeError, InvalidJsonError
from app.services.widget_cache.cache_service import CacheService

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

@router.post("/json", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def upload_json_connection(
    file: UploadFile = File(...),
    name: str = Form(...),
    user_session_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Sube un archivo JSON como fuente de datos estática.
    Valida el tamaño (<10MB) y la integridad del JSON.
    """
    if file.filename and not file.filename.endswith(".json"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a .json file")

    json_service = JsonFileService()
    
    try:
        # FastAPI's UploadFile.read() asíncrono
        content = await file.read()
        file_path, _ = await json_service.save_and_validate(content, file.filename or "upload.json")
    except FileTooLargeError as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))
    except InvalidJsonError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")

    # Crear modelo de dominio para el archivo
    new_connection = DataSourceConnection(
        user_session_id=user_session_id,
        name=name,
        source_type=DataSourceType.JSON,
        connection_string=file_path, # Guardamos la ruta física como connection_string
        status=ConnectionStatus.ACTIVE
    )

    repo = SQLiteConnectionRepository(db)
    saved_connection = await repo.save(new_connection)

    return saved_connection


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a connection and soft-invalidate all associated widget cache entries."""
    repo = SQLiteConnectionRepository(db)
    connection = await repo.find_by_id(connection_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    cache_service = CacheService(db)
    await cache_service.invalidate_by_connection(
        session_id=connection.user_session_id,
        connection_id=connection_id,
    )

    await repo.delete(connection_id)
    await db.commit()
