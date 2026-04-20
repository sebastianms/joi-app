import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

@pytest.mark.asyncio
async def test_lifespan_and_health_check():
    """
    Testea explícitamente el ciclo de vida (lifespan) de la app 
    (que inicializa la BD) y el endpoint /health.
    Usando AsyncClient como context manager para que emita
    el evento 'startup'/'shutdown'.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
