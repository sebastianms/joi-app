"""Integration test (T113): `POST /api/chat/messages` returns a ChatResponse
with a WidgetSpec validated against `widget-spec-v1.schema.json`.
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

WIDGET_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "004-widget-generation"
    / "contracts"
    / "widget-spec-v1.schema.json"
)


@pytest.fixture(scope="module")
def widget_schema() -> dict:
    with WIDGET_SCHEMA_PATH.open() as f:
        return json.load(f)


@pytest.fixture
def sqlite_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "fixture.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE sales (id INTEGER PRIMARY KEY, product TEXT, amount REAL);
        INSERT INTO sales (product, amount) VALUES ('A', 10.0), ('B', 20.0), ('C', 30.0);
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
        id="conn-widget",
        user_session_id="session-widget",
        name="fixture-widget",
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


def _widget_payload_for_bar_chart() -> str:
    """Minimal valid WidgetSpec the LLM would return for a bar chart."""
    return json.dumps(
        {
            "contract_version": "v1",
            "widget_id": "11111111-1111-1111-1111-111111111111",
            "extraction_id": "00000000-0000-0000-0000-000000000000",
            "session_id": "placeholder",
            "render_mode": "ui_framework",
            "ui_library": "shadcn",
            "widget_type": "bar_chart",
            "selection_source": "deterministic",
            "bindings": {"x": "product", "y": "amount"},
            "data_reference": {
                "extraction_id": "00000000-0000-0000-0000-000000000000",
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "product", "type": "string"},
                    {"name": "amount", "type": "float"},
                ],
                "row_count": 0,
            },
            "truncation_badge": False,
            "generated_by_model": "stub-widget-model",
        }
    )


@pytest.fixture
def _mock_litellm_sql_and_widget(monkeypatch):
    """Route SQL purpose → valid SELECT; widget purpose → valid WidgetSpec JSON."""

    async def fake_acompletion(messages, *, purpose, **kwargs):
        if purpose == "sql":
            return {
                "choices": [
                    {"message": {"content": "SELECT id, product, amount FROM sales ORDER BY id"}}
                ]
            }
        if purpose == "widget":
            return {"choices": [{"message": {"content": _widget_payload_for_bar_chart()}}]}
        raise AssertionError(f"unexpected purpose {purpose}")

    monkeypatch.setattr(sut_adapter.litellm_client, "acompletion", fake_acompletion)
    monkeypatch.setattr(litellm_client, "acompletion", fake_acompletion)


@pytest.mark.asyncio
async def test_chat_returns_widget_spec_conforming_to_schema(
    client: AsyncClient,
    seeded_connection: DataSourceConnection,
    _override_chat_manager,
    _mock_litellm_sql_and_widget,
    widget_schema: dict,
    monkeypatch,
):
    monkeypatch.setattr(sut_adapter.settings, "MAX_ROWS_PER_EXTRACTION", 100)

    payload = {
        "session_id": "session-widget",
        "message": "ventas por producto en un gráfico de barras",
    }

    response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["intent_type"] == "complex"
    assert data["extraction"]["status"] == "success"
    assert data["extraction"]["row_count"] == 3

    widget = data["widget_spec"]
    assert widget is not None

    jsonschema.validate(instance=widget, schema=widget_schema)

    assert widget["widget_type"] == "bar_chart"
    assert widget["render_mode"] == "ui_framework"
    assert widget["ui_library"] == "shadcn"
    assert widget["extraction_id"] == data["extraction"]["extraction_id"]
    assert widget["session_id"] == "session-widget"
    assert widget["data_reference"]["extraction_id"] == data["extraction"]["extraction_id"]


@pytest.mark.asyncio
async def test_chat_error_extraction_returns_no_widget_spec(
    client: AsyncClient,
    _override_chat_manager,
):
    """FR-015: extraction errors must not trigger widget generation."""
    payload = {
        "session_id": "session-no-conn",
        "message": "ventas por producto",
    }

    response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["extraction"]["status"] == "error"
    assert data["extraction"]["error"]["code"] == "NO_CONNECTION"
    assert data.get("widget_spec") is None


@pytest.mark.asyncio
async def test_chat_falls_back_to_table_when_generator_returns_invalid_spec(
    client: AsyncClient,
    seeded_connection: DataSourceConnection,
    _override_chat_manager,
    monkeypatch,
):
    """Invalid LLM response for widget purpose → fallback table, session stays healthy (FR-009)."""

    async def fake_acompletion(messages, *, purpose, **kwargs):
        if purpose == "sql":
            return {
                "choices": [
                    {"message": {"content": "SELECT id, product, amount FROM sales ORDER BY id"}}
                ]
            }
        if purpose == "widget":
            return {"choices": [{"message": {"content": "not valid json"}}]}
        raise AssertionError(f"unexpected purpose {purpose}")

    monkeypatch.setattr(sut_adapter.litellm_client, "acompletion", fake_acompletion)
    monkeypatch.setattr(litellm_client, "acompletion", fake_acompletion)
    monkeypatch.setattr(sut_adapter.settings, "MAX_ROWS_PER_EXTRACTION", 100)

    payload = {
        "session_id": "session-widget",
        "message": "ventas por producto",
    }

    response = await client.post("/api/chat/messages", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["widget_spec"]["widget_type"] == "table"
    assert data["widget_spec"]["selection_source"] == "fallback"
