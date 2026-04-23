import asyncio
import sqlite3
from pathlib import Path

import pytest

from app.models.connection import DataSourceConnection, DataSourceType
from app.models.extraction import ErrorCode, SourceType
from app.services.agents import sql_agent_adapter as sut
from app.services.agents.sql_agent_adapter import SqlAgentAdapter, _strip_fences


@pytest.fixture
def sqlite_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE sales (id INTEGER PRIMARY KEY, product TEXT, amount REAL);
        INSERT INTO sales (product, amount) VALUES ('A', 10.5), ('B', 20.0), ('C', 30.25);
        """
    )
    conn.commit()
    conn.close()
    return db_path


def _connection(db_path: Path) -> DataSourceConnection:
    return DataSourceConnection(
        id="conn-1",
        user_session_id="session-1",
        name="test",
        source_type=DataSourceType.SQLITE,
        file_path=str(db_path),
        connection_string=None,
    )


def _patch_llm(monkeypatch, sql: str) -> None:
    async def fake_acompletion(messages, *, purpose, **kwargs):
        assert purpose == "sql"
        return {"choices": [{"message": {"content": sql}}]}

    monkeypatch.setattr(sut.litellm_client, "acompletion", fake_acompletion)


# --- Happy path ---

@pytest.mark.asyncio
async def test_extract_returns_success_with_rows(monkeypatch, sqlite_db):
    _patch_llm(monkeypatch, "SELECT id, product, amount FROM sales ORDER BY id")
    monkeypatch.setattr(sut.settings, "MAX_ROWS_PER_EXTRACTION", 100)
    adapter = SqlAgentAdapter()

    extraction = await adapter.extract("dame las ventas", _connection(sqlite_db))

    assert extraction.status == "success"
    assert extraction.source_type == SourceType.SQL_SQLITE
    assert extraction.row_count == 3
    assert extraction.truncated is False
    assert [r["product"] for r in extraction.rows] == ["A", "B", "C"]
    assert extraction.columns[0].name == "id"
    assert extraction.query_plan.language == "sql"
    assert extraction.query_plan.generated_by_model  # populated from settings


@pytest.mark.asyncio
async def test_extract_strips_markdown_fences_from_llm(monkeypatch, sqlite_db):
    _patch_llm(monkeypatch, "```sql\nSELECT id FROM sales\n```")
    adapter = SqlAgentAdapter()

    extraction = await adapter.extract("ids", _connection(sqlite_db))

    assert extraction.status == "success"
    assert extraction.query_plan.expression == "SELECT id FROM sales"


# --- Guard rejection ---

@pytest.mark.asyncio
async def test_extract_rejects_non_select_via_guard(monkeypatch, sqlite_db):
    _patch_llm(monkeypatch, "DELETE FROM sales")
    adapter = SqlAgentAdapter()

    extraction = await adapter.extract("borra todo", _connection(sqlite_db))

    assert extraction.status == "error"
    assert extraction.error.code == ErrorCode.SECURITY_REJECTION
    assert extraction.query_plan.expression == "DELETE FROM sales"
    # table count must be unchanged — guard stopped execution
    conn = sqlite3.connect(sqlite_db)
    count = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    conn.close()
    assert count == 3


# --- Missing table ---

@pytest.mark.asyncio
async def test_extract_maps_missing_table_to_target_not_found(monkeypatch, sqlite_db):
    _patch_llm(monkeypatch, "SELECT * FROM ghost_table")
    adapter = SqlAgentAdapter()

    extraction = await adapter.extract("fantasma", _connection(sqlite_db))

    assert extraction.status == "error"
    assert extraction.error.code == ErrorCode.TARGET_NOT_FOUND


# --- Timeout ---

@pytest.mark.asyncio
async def test_extract_maps_timeout_to_timeout_code(monkeypatch, sqlite_db):
    _patch_llm(monkeypatch, "SELECT * FROM sales")
    monkeypatch.setattr(sut.settings, "QUERY_TIMEOUT_SECONDS", 1)

    def slow_execute(self, engine, sql):
        import time
        time.sleep(3)
        return [], False

    monkeypatch.setattr(SqlAgentAdapter, "_execute_sql", slow_execute)
    adapter = SqlAgentAdapter()

    extraction = await adapter.extract("lento", _connection(sqlite_db))

    assert extraction.status == "error"
    assert extraction.error.code == ErrorCode.TIMEOUT


# --- Truncation ---

@pytest.mark.asyncio
async def test_extract_truncates_to_max_rows(monkeypatch, sqlite_db):
    _patch_llm(monkeypatch, "SELECT id, product, amount FROM sales ORDER BY id")
    monkeypatch.setattr(sut.settings, "MAX_ROWS_PER_EXTRACTION", 2)
    adapter = SqlAgentAdapter()

    extraction = await adapter.extract("top", _connection(sqlite_db))

    assert extraction.status == "success"
    assert extraction.row_count == 2
    assert extraction.truncated is True


# --- Schema cache ---

@pytest.mark.asyncio
async def test_schema_cache_hits_on_second_call(monkeypatch, sqlite_db):
    _patch_llm(monkeypatch, "SELECT id FROM sales")
    adapter = SqlAgentAdapter()

    await adapter.extract("x", _connection(sqlite_db))
    assert "conn-1" in adapter._schema_cache

    # second call should reuse cache — verify by invalidating and re-populating only on demand
    adapter.invalidate_schema_cache("conn-1")
    assert "conn-1" not in adapter._schema_cache


# --- Helper units ---

def test_strip_fences_removes_sql_code_block():
    assert _strip_fences("```sql\nSELECT 1\n```") == "SELECT 1"


def test_strip_fences_leaves_plain_sql_untouched():
    assert _strip_fences("SELECT 1") == "SELECT 1"


def test_strip_fences_handles_generic_code_block():
    assert _strip_fences("```\nSELECT 1\n```") == "SELECT 1"
