"""End-to-end integration test: `POST /api/chat/messages` with SQLite fixture
and LiteLLM mocked. Validates the `data_extraction.v1` contract on the wire.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import jsonschema
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.chat import get_chat_manager
from app.main import app
from app.models.connection import ConnectionStatus, DataSourceConnection, DataSourceType
from app.services import litellm_client
from app.services.agents import sql_agent_adapter as sut_adapter
from app.services.chat_manager import ChatManagerService
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "003-data-agent"
    / "contracts"
    / "data-extraction-v1.schema.json"
)


@pytest.fixture(scope="module")
def extraction_schema() -> dict:
    with CONTRACT_PATH.open() as f:
        return json.load(f)


@pytest.fixture
def sqlite_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "fixture.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE sales (id INTEGER PRIMARY KEY, product TEXT, amount REAL);
        INSERT INTO sales (product, amount) VALUES ('A', 10.0), ('B', 20.0);
        """
    )
    conn.commit()
    conn.close()
    return db_path


class _EchoLLM(LLMGateway):
    def complete(self, history):
        return "unused"


@pytest_asyncio.fixture
async def seeded_connection(
    db_session: AsyncSession, sqlite_db: Path
) -> DataSourceConnection:
    connection = DataSourceConnection(
        id="conn-e2e",
        user_session_id="session-e2e",
        name="fixture",
        source_type=DataSourceType.SQLITE,
        file_path=str(sqlite_db),
        connection_string=None,
        status=ConnectionStatus.ACTIVE,
    )
    db_session.add(connection)
    await db_session.commit()
    return connection


@pytest.fixture
def _override_chat_manager():
    fresh_manager = ChatManagerService(
        triage=TriageEngineService(),
        llm=_EchoLLM(),
    )
    app.dependency_overrides[get_chat_manager] = lambda: fresh_manager
    yield
    app.dependency_overrides.pop(get_chat_manager, None)


@pytest.fixture
def _mock_litellm(monkeypatch):
    async def fake_acompletion(messages, *, purpose, **kwargs):
        assert purpose == "sql"
        return {
            "choices": [
                {"message": {"content": "SELECT id, product, amount FROM sales ORDER BY id"}}
            ]
        }

    monkeypatch.setattr(sut_adapter.litellm_client, "acompletion", fake_acompletion)
    monkeypatch.setattr(litellm_client, "acompletion", fake_acompletion)


@pytest.mark.asyncio
async def test_chat_complex_intent_returns_contract_compliant_extraction(
    client: AsyncClient,
    seeded_connection: DataSourceConnection,
    _override_chat_manager,
    _mock_litellm,
    extraction_schema: dict,
):
    payload = {
        "session_id": "session-e2e",
        "message": "muéstrame las ventas por producto",
    }

    response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["intent_type"] == "complex"
    assert data["response"] == "Encontré 2 filas."

    extraction = data["extraction"]
    jsonschema.validate(instance=extraction, schema=extraction_schema)

    assert extraction["status"] == "success"
    assert extraction["source_type"] == "SQL_SQLITE"
    assert extraction["row_count"] == 2
    assert extraction["truncated"] is False
    assert [r["product"] for r in extraction["rows"]] == ["A", "B"]
    assert {c["name"] for c in extraction["columns"]} == {"id", "product", "amount"}
    assert extraction["query_plan"]["language"] == "sql"
    assert "SELECT" in extraction["query_plan"]["expression"]

    trace = data["trace"]
    assert trace["pipeline"] == "sql"
    assert trace["extraction_id"] == extraction["extraction_id"]
    assert trace["security_rejection"] is False
    assert len(trace["preview_rows"]) == 2


@pytest.mark.asyncio
async def test_chat_complex_intent_without_connection_returns_no_connection_error(
    client: AsyncClient,
    _override_chat_manager,
    extraction_schema: dict,
):
    payload = {
        "session_id": "session-without-conn",
        "message": "dame un análisis de ventas",
    }

    response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()

    extraction = data["extraction"]
    jsonschema.validate(instance=extraction, schema=extraction_schema)

    assert extraction["status"] == "error"
    assert extraction["error"]["code"] == "NO_CONNECTION"
    assert "/setup" in data["response"]
