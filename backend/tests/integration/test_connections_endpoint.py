from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.main import app
from app.models.connection import DataSourceType, ConnectionStatus


@pytest.mark.asyncio
@patch("app.api.endpoints.connections.ConnectionTesterService")
async def test_create_sql_connection_success(mock_tester_class, db_session: AsyncSession):
    # Sobrescribir la dependencia para usar la BD de tests en memoria
    app.dependency_overrides[get_db] = lambda: db_session

    # Setup del mock de tester
    mock_tester_instance = AsyncMock()
    mock_tester_instance.test_connection.return_value = (True, None)
    mock_tester_class.return_value = mock_tester_instance

    payload = {
        "user_session_id": "sess-test",
        "name": "My Postgres",
        "connection_string": "postgresql+asyncpg://usr:pass@localhost/db",
        "source_type": DataSourceType.POSTGRESQL.value,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/connections/sql", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "My Postgres"
    assert data["status"] == ConnectionStatus.ACTIVE.value
    assert data["source_type"] == DataSourceType.POSTGRESQL.value

    # Verificar que el servicio fue llamado
    mock_tester_instance.test_connection.assert_called_once_with(
        "postgresql+asyncpg://usr:pass@localhost/db"
    )

    # Limpiar override
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@patch("app.api.endpoints.connections.ConnectionTesterService")
async def test_create_sql_connection_failure(mock_tester_class):
    # Setup del mock
    mock_tester_instance = AsyncMock()
    # Retorna is_valid=False, error="Auth failed"
    mock_tester_instance.test_connection.return_value = (False, "Auth failed")
    mock_tester_class.return_value = mock_tester_instance

    payload = {
        "user_session_id": "sess-test",
        "name": "Invalid DB",
        "connection_string": "sqlite+aiosqlite:////invalid.db",
        "source_type": DataSourceType.SQLITE.value,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/connections/sql", json=payload)

    # El endpoint debe retornar 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Auth failed" in data["detail"]
