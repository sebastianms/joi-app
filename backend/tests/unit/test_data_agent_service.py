import sqlite3
from pathlib import Path
from typing import Any

import pytest

from app.models.connection import DataSourceConnection, DataSourceType
from app.models.extraction import (
    ColumnDescriptor,
    DataExtraction,
    ErrorCode,
    ExtractionError,
    QueryPlan,
    SourceType,
)
from app.models.user_session import UserSession
from app.services.agents.sql_agent_adapter import SqlAgentAdapter
from app.services.data_agent_service import DataAgentService


class FakeConnectionRepo:
    def __init__(self, connections: list[DataSourceConnection]) -> None:
        self._connections = connections

    async def find_by_session(self, session_id: str) -> list[DataSourceConnection]:
        return [c for c in self._connections if c.user_session_id == session_id]


class FakeSessionRepo:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def get_or_create(self, session_id: str) -> UserSession:
        self.calls.append(session_id)
        return UserSession(session_id=session_id)


class StubSqlAdapter:
    def __init__(self, extraction: DataExtraction) -> None:
        self._extraction = extraction
        self.calls: list[tuple[str, str]] = []

    async def extract(
        self, prompt: str, connection: DataSourceConnection
    ) -> DataExtraction:
        self.calls.append((prompt, connection.id))
        return self._extraction


def _connection(
    source_type: DataSourceType = DataSourceType.SQLITE,
    session_id: str = "session-1",
) -> DataSourceConnection:
    return DataSourceConnection(
        id="conn-1",
        user_session_id=session_id,
        name="test",
        source_type=source_type,
        file_path="/tmp/irrelevant.db" if source_type == DataSourceType.SQLITE else None,
        connection_string=None if source_type == DataSourceType.SQLITE else "x",
    )


def _success_extraction() -> DataExtraction:
    return DataExtraction(
        session_id="session-1",
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression="SELECT 1"),
        columns=[ColumnDescriptor(name="x", type="integer")],
        rows=[{"x": 1}, {"x": 2}, {"x": 3}],
        row_count=3,
        status="success",
    )


def _rejected_extraction() -> DataExtraction:
    return DataExtraction(
        session_id="session-1",
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression="DELETE FROM x"),
        row_count=0,
        status="error",
        error=ExtractionError(
            code=ErrorCode.SECURITY_REJECTION, message="bloqueado"
        ),
    )


@pytest.mark.asyncio
async def test_extract_returns_no_connection_when_session_has_none():
    service = DataAgentService(
        connection_repo=FakeConnectionRepo([]),
        session_repo=FakeSessionRepo(),
        sql_adapter=StubSqlAdapter(_success_extraction()),
    )

    extraction, trace = await service.extract("session-1", "dame datos")

    assert extraction.status == "error"
    assert extraction.error.code == ErrorCode.NO_CONNECTION
    assert trace.extraction_id == extraction.extraction_id
    assert trace.pipeline == "sql"
    assert trace.query_display == ""


@pytest.mark.asyncio
async def test_extract_routes_sql_sources_to_sql_adapter():
    conn = _connection(DataSourceType.SQLITE)
    stub = StubSqlAdapter(_success_extraction())
    service = DataAgentService(
        connection_repo=FakeConnectionRepo([conn]),
        session_repo=FakeSessionRepo(),
        sql_adapter=stub,
    )

    extraction, trace = await service.extract("session-1", "ventas")

    assert extraction.status == "success"
    assert stub.calls == [("ventas", "conn-1")]
    assert trace.pipeline == "sql"
    assert trace.query_display == "SELECT 1"
    assert trace.preview_rows == [{"x": 1}, {"x": 2}, {"x": 3}]


@pytest.mark.asyncio
async def test_trace_flags_security_rejection():
    conn = _connection(DataSourceType.SQLITE)
    service = DataAgentService(
        connection_repo=FakeConnectionRepo([conn]),
        session_repo=FakeSessionRepo(),
        sql_adapter=StubSqlAdapter(_rejected_extraction()),
    )

    _, trace = await service.extract("session-1", "borra todo")

    assert trace.security_rejection is True


@pytest.mark.asyncio
async def test_trace_respects_preview_row_limit(monkeypatch):
    from app.services import data_agent_service as sut

    monkeypatch.setattr(sut.settings, "TRACE_PREVIEW_ROWS", 2)

    conn = _connection(DataSourceType.SQLITE)
    service = DataAgentService(
        connection_repo=FakeConnectionRepo([conn]),
        session_repo=FakeSessionRepo(),
        sql_adapter=StubSqlAdapter(_success_extraction()),
    )

    _, trace = await service.extract("session-1", "x")

    assert len(trace.preview_rows) == 2


@pytest.mark.asyncio
async def test_json_source_returns_unsupported_error():
    conn = _connection(DataSourceType.JSON)
    service = DataAgentService(
        connection_repo=FakeConnectionRepo([conn]),
        session_repo=FakeSessionRepo(),
        sql_adapter=StubSqlAdapter(_success_extraction()),
    )

    extraction, trace = await service.extract("session-1", "x")

    assert extraction.status == "error"
    assert extraction.source_type == SourceType.JSON
    assert trace.pipeline == "json"


@pytest.mark.asyncio
async def test_extract_materializes_user_session():
    session_repo = FakeSessionRepo()
    service = DataAgentService(
        connection_repo=FakeConnectionRepo([]),
        session_repo=session_repo,
        sql_adapter=StubSqlAdapter(_success_extraction()),
    )

    await service.extract("session-42", "x")

    assert session_repo.calls == ["session-42"]
