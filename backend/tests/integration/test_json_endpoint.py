import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.main import app
from app.db.session import get_db
from app.models.connection import DataSourceType, ConnectionStatus
from app.services.json_handler import JsonFileService

@pytest.fixture
def mock_upload_dir(tmp_path):
    # Parcheamos la ruta por defecto del JsonFileService en el entorno de tests
    return str(tmp_path / "uploads")

@pytest.mark.asyncio
async def test_upload_json_success(db_session: AsyncSession, mock_upload_dir: str):
    app.dependency_overrides[get_db] = lambda: db_session

    valid_json_content = b'{"hello": "world"}'
    
    from unittest.mock import AsyncMock
    # Parcheamos la inicialización del servicio en el endpoint
    with patch("app.api.endpoints.connections.JsonFileService") as mock_service_class:
        mock_instance = mock_service_class.return_value
        mock_instance.save_and_validate = AsyncMock(return_value=(f"{mock_upload_dir}/file.json", {"hello": "world"}))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/connections/json",
                data={
                    "name": "My JSON Data",
                    "user_session_id": "sess-test-json"
                },
                files={"file": ("data.json", valid_json_content, "application/json")}
            )

    print(response.json())
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "My JSON Data"
    assert data["source_type"] == DataSourceType.JSON.value
    assert data["status"] == ConnectionStatus.ACTIVE.value

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_upload_json_wrong_extension(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/connections/json",
            data={
                "name": "My JSON Data",
                "user_session_id": "sess-test-json"
            },
            files={"file": ("data.txt", b"plain text", "text/plain")}
        )

    assert response.status_code == 400
    assert "File must be a .json file" in response.json()["detail"]

    app.dependency_overrides.clear()
