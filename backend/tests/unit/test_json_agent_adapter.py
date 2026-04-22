"""Unit tests for JsonAgentAdapter (T027).

Mocks litellm_client.acompletion; uses products_sample.json fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models.connection import ConnectionStatus, DataSourceConnection, DataSourceType
from app.models.extraction import ErrorCode
from app.services.agents import json_agent_adapter as sut

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "products_sample.json"


def _connection(file_path: str) -> DataSourceConnection:
    return DataSourceConnection(
        id="conn-json",
        user_session_id="session-json",
        name="products",
        source_type=DataSourceType.JSON,
        file_path=file_path,
        connection_string=None,
        status=ConnectionStatus.ACTIVE,
    )


def _mock_llm(monkeypatch, expression: str) -> None:
    async def fake_acompletion(messages, *, purpose, **kwargs):
        assert purpose == "json"
        return {"choices": [{"message": {"content": expression}}]}

    monkeypatch.setattr(sut.litellm_client, "acompletion", fake_acompletion)


@pytest.mark.asyncio
async def test_filter_by_category(monkeypatch, tmp_path):
    """JSONPath filter that returns a subset of products."""
    products = json.loads(FIXTURE_PATH.read_text())
    db = tmp_path / "products.json"
    db.write_text(json.dumps(products))

    _mock_llm(monkeypatch, "$[?(@.category=='Electrónica')]")

    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("productos de Electrónica", _connection(str(db)))

    assert extraction.status == "success"
    assert extraction.source_type.value == "JSON"
    assert extraction.row_count > 0
    assert all(r["category"] == "Electrónica" for r in extraction.rows)
    assert extraction.query_plan.language == "jsonpath"
    assert "Electrónica" in extraction.query_plan.expression


@pytest.mark.asyncio
async def test_all_items_returned(monkeypatch, tmp_path):
    """JSONPath that selects all items returns complete dataset."""
    products = json.loads(FIXTURE_PATH.read_text())
    db = tmp_path / "products.json"
    db.write_text(json.dumps(products))

    _mock_llm(monkeypatch, "$[*]")

    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("todos los productos", _connection(str(db)))

    assert extraction.status == "success"
    assert extraction.row_count == len(products)
    assert extraction.truncated is False


@pytest.mark.asyncio
async def test_truncation(monkeypatch, tmp_path):
    """Results truncated when they exceed MAX_ROWS_PER_EXTRACTION."""
    products = json.loads(FIXTURE_PATH.read_text())
    db = tmp_path / "products.json"
    db.write_text(json.dumps(products))

    monkeypatch.setattr(sut.settings, "MAX_ROWS_PER_EXTRACTION", 3)
    _mock_llm(monkeypatch, "$[*]")

    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("todos", _connection(str(db)))

    assert extraction.status == "success"
    assert extraction.row_count == 3
    assert extraction.truncated is True


@pytest.mark.asyncio
async def test_invalid_jsonpath(monkeypatch, tmp_path):
    """Invalid JSONPath expression maps to QUERY_SYNTAX error."""
    db = tmp_path / "data.json"
    db.write_text(json.dumps([{"x": 1}]))

    _mock_llm(monkeypatch, "NOT_A_VALID_JSONPATH[[[")

    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("algo", _connection(str(db)))

    assert extraction.status == "error"
    assert extraction.error.code == ErrorCode.QUERY_SYNTAX


@pytest.mark.asyncio
async def test_target_not_found(monkeypatch):
    """Missing file maps to TARGET_NOT_FOUND error."""
    _mock_llm(monkeypatch, "$[*]")

    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("algo", _connection("/nonexistent/path.json"))

    assert extraction.status == "error"
    assert extraction.error.code == ErrorCode.TARGET_NOT_FOUND


@pytest.mark.asyncio
async def test_invalid_json_file(monkeypatch, tmp_path):
    """Corrupt JSON file maps to QUERY_SYNTAX error."""
    db = tmp_path / "bad.json"
    db.write_text("{ not valid json }")

    _mock_llm(monkeypatch, "$[*]")

    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("algo", _connection(str(db)))

    assert extraction.status == "error"
    assert extraction.error.code == ErrorCode.QUERY_SYNTAX


@pytest.mark.asyncio
async def test_empty_result(monkeypatch, tmp_path):
    """JSONPath that matches nothing returns success with zero rows."""
    db = tmp_path / "data.json"
    db.write_text(json.dumps([{"category": "A"}, {"category": "B"}]))

    _mock_llm(monkeypatch, "$[?(@.category=='Z')]")

    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("categoría Z", _connection(str(db)))

    assert extraction.status == "success"
    assert extraction.row_count == 0
    assert extraction.rows == []
    assert extraction.truncated is False


@pytest.mark.asyncio
async def test_non_object_matches_wrapped(monkeypatch, tmp_path):
    """Scalar JSONPath matches are wrapped in {'value': ...} dicts."""
    db = tmp_path / "data.json"
    db.write_text(json.dumps({"prices": [10, 20, 30]}))

    _mock_llm(monkeypatch, "$.prices[*]")

    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("precios", _connection(str(db)))

    assert extraction.status == "success"
    assert extraction.row_count == 3
    assert all("value" in r for r in extraction.rows)


@pytest.mark.asyncio
async def test_columns_detected_from_first_row(monkeypatch, tmp_path):
    """Column descriptors are inferred from the first matching object."""
    db = tmp_path / "data.json"
    db.write_text(json.dumps([{"id": 1, "name": "X", "price": 9.9}]))

    _mock_llm(monkeypatch, "$[*]")

    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("todo", _connection(str(db)))

    col_names = {c.name for c in extraction.columns}
    assert col_names == {"id", "name", "price"}


@pytest.mark.asyncio
async def test_no_file_path_configured(monkeypatch):
    """Connection without file_path returns SOURCE_UNAVAILABLE."""
    conn = DataSourceConnection(
        id="conn-nopath",
        user_session_id="s",
        name="empty",
        source_type=DataSourceType.JSON,
        file_path=None,
        connection_string=None,
        status=ConnectionStatus.ACTIVE,
    )
    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("algo", conn)

    assert extraction.status == "error"
    assert extraction.error.code == ErrorCode.SOURCE_UNAVAILABLE


@pytest.mark.asyncio
async def test_llm_returns_fenced_expression(monkeypatch, tmp_path):
    """Markdown code fences in LLM response are stripped."""
    db = tmp_path / "data.json"
    db.write_text(json.dumps([{"x": 1}]))

    _mock_llm(monkeypatch, "```json\n$[*]\n```")

    adapter = sut.JsonAgentAdapter()
    extraction = await adapter.extract("algo", _connection(str(db)))

    assert extraction.status == "success"
    assert extraction.query_plan.expression == "$[*]"
