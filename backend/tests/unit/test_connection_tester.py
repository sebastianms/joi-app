from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.services.connection_tester import ConnectionTesterService


@pytest.fixture
def service() -> ConnectionTesterService:
    return ConnectionTesterService()


@pytest.mark.asyncio
@patch("app.services.connection_tester.create_async_engine")
async def test_test_connection_success(mock_create_engine, service: ConnectionTesterService):
    # Setup del mock
    mock_engine = AsyncMock()
    mock_conn = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_engine.connect = MagicMock(return_value=mock_context)
    mock_create_engine.return_value = mock_engine

    # Acción
    is_valid, error = await service.test_connection("sqlite+aiosqlite:///:memory:")

    # Verificación
    assert is_valid is True
    assert error is None
    mock_create_engine.assert_called_once_with("sqlite+aiosqlite:///:memory:", echo=False)
    mock_engine.connect.assert_called_once()
    mock_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.services.connection_tester.create_async_engine")
async def test_test_connection_failure_sqlalchemy_error(
    mock_create_engine, service: ConnectionTesterService
):
    # Setup del mock para que lance error al conectar
    mock_engine = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.side_effect = SQLAlchemyError("Authentication failed")
    mock_engine.connect = MagicMock(return_value=mock_context)
    mock_create_engine.return_value = mock_engine

    # Acción
    is_valid, error = await service.test_connection("postgresql+asyncpg://user:pass@host/db")

    # Verificación
    assert is_valid is False
    assert "Authentication failed" in error
    mock_create_engine.assert_called_once_with("postgresql+asyncpg://user:pass@host/db", echo=False)
    mock_engine.connect.assert_called_once()
    mock_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_test_connection_failure_invalid_url_scheme(service: ConnectionTesterService):
    # Acción: URL totalmente mal formada
    is_valid, error = await service.test_connection("not-a-db-url")

    # Verificación
    assert is_valid is False
    assert "Invalid URL" in error or "Could not parse" in error
