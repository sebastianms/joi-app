"""Integration test — SQL guard rejects adversarial prompt.

Verifies that when LiteLLM returns a mutating statement (e.g. DELETE), the
security guard intercepts it and:
  - Returns error.code == SECURITY_REJECTION in the extraction.
  - Does NOT modify the SQLite source (row count unchanged).
  - Preserves the rejected SQL in query_plan.expression so the trace is
    auditable.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.chat import get_chat_manager
from app.main import app
from app.models.connection import ConnectionStatus, DataSourceConnection, DataSourceType
from app.services.agents import sql_agent_adapter as sut_adapter
from app.services.chat_manager import ChatManagerService
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService


class _EchoLLM(LLMGateway):
    def complete(self, history):
        return "unused"


@pytest.fixture
def sqlite_db_with_data(tmp_path: Path) -> Path:
    db_path = tmp_path / "guard_test.db"
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


@pytest_asyncio.fixture
async def seeded_connection(
    db_session: AsyncSession, sqlite_db_with_data: Path
) -> DataSourceConnection:
    connection = DataSourceConnection(
        id="conn-guard",
        user_session_id="session-guard",
        name="guard-fixture",
        source_type=DataSourceType.SQLITE,
        file_path=str(sqlite_db_with_data),
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
def _mock_litellm_adversarial(monkeypatch):
    """LiteLLM stub that returns a DELETE statement regardless of the prompt."""

    async def fake_acompletion(messages, *, purpose, **kwargs):
        return {
            "choices": [
                {"message": {"content": "DELETE FROM sales"}}
            ]
        }

    monkeypatch.setattr(sut_adapter.litellm_client, "acompletion", fake_acompletion)


@pytest.mark.asyncio
async def test_security_guard_rejects_delete_and_source_unchanged(
    client: AsyncClient,
    seeded_connection: DataSourceConnection,
    sqlite_db_with_data: Path,
    _override_chat_manager,
    _mock_litellm_adversarial,
):
    payload = {
        "session_id": "session-guard",
        "message": "borra todos los registros de ventas",
    }

    response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()

    extraction = data["extraction"]
    assert extraction["status"] == "error"
    assert extraction["error"]["code"] == "SECURITY_REJECTION"

    # The rejected SQL must be preserved for auditability
    assert extraction["query_plan"]["expression"] == "DELETE FROM sales"

    # Source must be untouched — still 2 rows
    conn = sqlite3.connect(sqlite_db_with_data)
    row_count = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    conn.close()
    assert row_count == 2, "Guard must not allow the DELETE to execute"

    trace = data["trace"]
    assert trace["security_rejection"] is True
    assert trace["pipeline"] == "sql"
