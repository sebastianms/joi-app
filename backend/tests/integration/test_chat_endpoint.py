import pytest
from httpx import AsyncClient, ASGITransport

from app.api.endpoints.chat import get_chat_manager, get_data_agent
from app.main import app
from app.models.chat import Message
from app.models.extraction import (
    AgentTrace,
    DataExtraction,
    ErrorCode,
    ExtractionError,
    QueryPlan,
    SourceType,
)
from app.services.chat_manager import ChatManagerService
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService


class _EchoStubLLM(LLMGateway):
    def complete(self, history: list[Message]) -> str:
        if not history:
            return "Echo: "
        return f"Echo: {history[-1].content}"


class _StubDataAgent:
    async def extract(
        self, session_id: str, prompt: str
    ) -> tuple[DataExtraction, AgentTrace]:
        extraction = DataExtraction(
            session_id=session_id,
            connection_id="__none__",
            source_type=SourceType.SQL_SQLITE,
            query_plan=QueryPlan(language="sql", expression=""),
            row_count=0,
            status="error",
            error=ExtractionError(
                code=ErrorCode.NO_CONNECTION,
                message="No hay una fuente de datos activa.",
            ),
        )
        trace = AgentTrace(
            extraction_id=extraction.extraction_id,
            pipeline="sql",
            query_display="",
        )
        return extraction, trace


@pytest.fixture(autouse=True)
def _override_dependencies():
    app.dependency_overrides[get_chat_manager] = lambda: ChatManagerService(
        triage=TriageEngineService(),
        llm=_EchoStubLLM(),
    )
    app.dependency_overrides[get_data_agent] = lambda: _StubDataAgent()
    yield
    app.dependency_overrides.pop(get_chat_manager, None)
    app.dependency_overrides.pop(get_data_agent, None)


@pytest.mark.asyncio
async def test_chat_simple_intent():
    payload = {"session_id": "s1", "message": "hola"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["intent_type"] == "simple"
    assert data["response"] == "Echo: hola"
    assert "extraction" not in data
    assert "trace" not in data


@pytest.mark.asyncio
async def test_chat_complex_intent_returns_extraction_contract():
    payload = {"session_id": "s2", "message": "muéstrame las ventas por mes"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["intent_type"] == "complex"
    assert data["extraction"]["status"] == "error"
    assert data["extraction"]["error"]["code"] == "NO_CONNECTION"
    assert data["trace"]["pipeline"] == "sql"
    assert "No hay una fuente de datos activa" in data["response"]


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
