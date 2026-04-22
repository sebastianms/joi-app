"""Data Agent fachada: orquesta adapters y construye trazas para el chat.

Resuelve la `DataSourceConnection` activa del `session_id`, enruta al adapter
según `source_type` (SQL vs JSON), y empaqueta el resultado como
`(DataExtraction, AgentTrace)`.

El campo `UserSession.rag_enabled` se lee pero no se usa en MVP (ADL-010);
se mantiene para forward-compat con US5.
"""

from __future__ import annotations

from app.core.config import settings
from app.models.connection import DataSourceConnection, DataSourceType
from app.models.extraction import (
    AgentTrace,
    DataExtraction,
    ErrorCode,
    ExtractionError,
    QueryPlan,
    SourceType,
)
from app.repositories.connection_repository import SQLiteConnectionRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.services.agents.json_agent_adapter import JsonAgentAdapter
from app.services.agents.sql_agent_adapter import SqlAgentAdapter

_SQL_TYPES = {
    DataSourceType.POSTGRESQL,
    DataSourceType.MYSQL,
    DataSourceType.SQLITE,
}

_SOURCE_TYPE_FOR_NO_CONNECTION = SourceType.SQL_SQLITE


class DataAgentService:
    def __init__(
        self,
        connection_repo: SQLiteConnectionRepository,
        session_repo: UserSessionRepository,
        sql_adapter: SqlAgentAdapter,
        json_adapter: JsonAgentAdapter | None = None,
    ) -> None:
        self._connections = connection_repo
        self._sessions = session_repo
        self._sql_adapter = sql_adapter
        self._json_adapter = json_adapter or JsonAgentAdapter()

    async def extract(
        self, session_id: str, prompt: str
    ) -> tuple[DataExtraction, AgentTrace]:
        await self._sessions.get_or_create(session_id)

        connection = await self._resolve_active_connection(session_id)
        if connection is None:
            extraction = self._no_connection_extraction(session_id)
            return extraction, self._build_trace(extraction, pipeline="sql")

        if connection.source_type in _SQL_TYPES:
            extraction = await self._sql_adapter.extract(prompt, connection)
            return extraction, self._build_trace(extraction, pipeline="sql")

        extraction = await self._json_adapter.extract(prompt, connection)
        return extraction, self._build_trace(extraction, pipeline="json")

    async def _resolve_active_connection(
        self, session_id: str
    ) -> DataSourceConnection | None:
        connections = await self._connections.find_by_session(session_id)
        return connections[0] if connections else None

    def _no_connection_extraction(self, session_id: str) -> DataExtraction:
        query_plan = QueryPlan(language="sql", expression="")
        return DataExtraction(
            session_id=session_id,
            connection_id="__none__",
            source_type=_SOURCE_TYPE_FOR_NO_CONNECTION,
            query_plan=query_plan,
            row_count=0,
            status="error",
            error=ExtractionError(
                code=ErrorCode.NO_CONNECTION,
                message=(
                    "No hay una fuente de datos activa para esta sesión. "
                    "Configura una conexión en /setup antes de continuar."
                ),
            ),
        )

    def _build_trace(
        self, extraction: DataExtraction, *, pipeline: str
    ) -> AgentTrace:
        preview_limit = settings.TRACE_PREVIEW_ROWS
        preview_rows = extraction.rows[:preview_limit]
        return AgentTrace(
            extraction_id=extraction.extraction_id,
            pipeline=pipeline,  # type: ignore[arg-type]
            query_display=extraction.query_plan.expression,
            preview_rows=preview_rows,
            preview_columns=extraction.columns,
            security_rejection=(
                extraction.status == "error"
                and extraction.error is not None
                and extraction.error.code == ErrorCode.SECURITY_REJECTION
            ),
        )
