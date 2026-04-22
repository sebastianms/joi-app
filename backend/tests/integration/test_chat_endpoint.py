import pytest
from httpx import AsyncClient, ASGITransport

from app.api.endpoints.chat import get_chat_manager
from app.main import app
from app.models.chat import Message
from app.services.chat_manager import ChatManagerService
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService


class _EchoStubLLM(LLMGateway):
    def complete(self, history: list[Message]) -> str:
        if not history:
            return "Echo: "
        return f"Echo: {history[-1].content}"


@pytest.fixture(autouse=True)
def _override_chat_manager():
    app.dependency_overrides[get_chat_manager] = lambda: ChatManagerService(
        triage=TriageEngineService(),
        llm=_EchoStubLLM(),
    )
    yield
    app.dependency_overrides.pop(get_chat_manager, None)


@pytest.mark.asyncio
async def test_chat_simple_intent():
    payload = {"session_id": "s1", "message": "hola"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["intent_type"] == "simple"
    assert data["response"] == "Echo: hola"


@pytest.mark.asyncio
async def test_chat_complex_intent():
    payload = {"session_id": "s2", "message": "muéstrame las ventas por mes"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["intent_type"] == "complex"
    assert "agentes" in data["response"] or "Pipeline" in data["response"]


@pytest.mark.asyncio
async def test_chat_default_simple_intent():
    payload = {"session_id": "s3", "message": "necesito ayuda con algo"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["intent_type"] == "simple"
    assert data["response"] == "Echo: necesito ayuda con algo"


@pytest.mark.asyncio
async def test_chat_validation_empty_message():
    payload = {"session_id": "s4", "message": ""}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_validation_missing_session_id():
    payload = {"message": "hola"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 422