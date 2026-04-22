"""SQL pipeline adapter: NL prompt → SQL → guard → execute → DataExtraction.

Implements the three-step linear pipeline established in ADL-009:

    generate (LiteLLM, purpose="sql")
        → validate (ReadOnlySqlGuard, ADL-005)
            → execute (SQLAlchemy, with timeout + row truncation)
                → DataExtraction

No external Text-to-SQL framework is used. The LLM call goes through the
singleton `litellm_client` (ADL-006 invariant preserved).
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import decimal as _decimal
import re
from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

from app.core.config import settings
from app.models.connection import DataSourceConnection, DataSourceType
from app.models.extraction import (
    ColumnDescriptor,
    DataExtraction,
    ErrorCode,
    ExtractionError,
    QueryPlan,
    SourceType,
)
from app.services import litellm_client
from app.services.read_only_sql_guard import (
    ReadOnlySqlGuard,
    SecurityRejectionError,
)


_SOURCE_TYPE_MAP: dict[DataSourceType, SourceType] = {
    DataSourceType.POSTGRESQL: SourceType.SQL_POSTGRESQL,
    DataSourceType.MYSQL: SourceType.SQL_MYSQL,
    DataSourceType.SQLITE: SourceType.SQL_SQLITE,
}

_DIALECT_LABEL: dict[DataSourceType, str] = {
    DataSourceType.POSTGRESQL: "PostgreSQL",
    DataSourceType.MYSQL: "MySQL",
    DataSourceType.SQLITE: "SQLite",
}

_FENCE_RE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class _TableSchema:
    name: str
    columns: list[tuple[str, str]]  # (name, type_str)


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()


def _build_dsn(connection: DataSourceConnection) -> str:
    if connection.source_type == DataSourceType.SQLITE:
        if connection.file_path:
            return f"sqlite:///{connection.file_path}"
        if connection.connection_string:
            # Strip async driver prefix saved by the setup wizard (aiosqlite → pysqlite)
            return connection.connection_string.replace(
                "sqlite+aiosqlite://", "sqlite://"
            )
        raise ValueError("SQLite connection missing both file_path and connection_string")
    if not connection.connection_string:
        raise ValueError(f"{connection.source_type.value} connection missing connection_string")
    return connection.connection_string


def _coerce_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, _decimal.Decimal):
        return float(value)
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    return str(value)


def _infer_column_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    return "unknown"


class SqlAgentAdapter:
    """Generates and executes SQL for a `DataSourceConnection`."""

    def __init__(self) -> None:
        self._schema_cache: dict[str, list[_TableSchema]] = {}

    async def extract(
        self,
        prompt: str,
        connection: DataSourceConnection,
    ) -> DataExtraction:
        source_type = _SOURCE_TYPE_MAP[connection.source_type]
        dsn = _build_dsn(connection)
        engine = sa.create_engine(dsn)
        try:
            schema = await asyncio.to_thread(self._get_schema, engine, connection.id)
            sql = await self._generate_sql(prompt, connection.source_type, schema)
            query_plan = QueryPlan(
                language="sql",
                expression=sql,
                generated_by_model=settings.LLM_MODEL_SQL,
            )

            try:
                ReadOnlySqlGuard.validate(sql)
            except SecurityRejectionError as exc:
                return self._error_extraction(
                    connection=connection,
                    source_type=source_type,
                    query_plan=query_plan,
                    code=ErrorCode.SECURITY_REJECTION,
                    message=f"Consulta rechazada por el guard de solo lectura: {exc.reason}",
                    technical=exc.reason,
                )

            try:
                rows, truncated = await asyncio.wait_for(
                    asyncio.to_thread(self._execute_sql, engine, sql),
                    timeout=settings.QUERY_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                return self._error_extraction(
                    connection=connection,
                    source_type=source_type,
                    query_plan=query_plan,
                    code=ErrorCode.TIMEOUT,
                    message=(
                        f"La consulta excedió el tiempo límite de "
                        f"{settings.QUERY_TIMEOUT_SECONDS}s."
                    ),
                )
            except SQLAlchemyError as exc:
                code, message = _classify_sqlalchemy_error(exc)
                return self._error_extraction(
                    connection=connection,
                    source_type=source_type,
                    query_plan=query_plan,
                    code=code,
                    message=message,
                    technical=str(exc.orig) if getattr(exc, "orig", None) else str(exc),
                )

            columns = _columns_from_rows(rows)
            return DataExtraction(
                session_id=connection.user_session_id,
                connection_id=connection.id,
                source_type=source_type,
                query_plan=query_plan,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
                status="success",
            )
        finally:
            engine.dispose()

    def _get_schema(self, engine: Engine, connection_id: str) -> list[_TableSchema]:
        if connection_id in self._schema_cache:
            return self._schema_cache[connection_id]
        inspector = sa.inspect(engine)
        tables: list[_TableSchema] = []
        for table_name in inspector.get_table_names():
            cols = [
                (col["name"], str(col["type"]))
                for col in inspector.get_columns(table_name)
            ]
            tables.append(_TableSchema(name=table_name, columns=cols))
        self._schema_cache[connection_id] = tables
        return tables

    def invalidate_schema_cache(self, connection_id: str) -> None:
        self._schema_cache.pop(connection_id, None)

    async def _generate_sql(
        self,
        prompt: str,
        source_type: DataSourceType,
        schema: list[_TableSchema],
    ) -> str:
        dialect = _DIALECT_LABEL[source_type]
        schema_text = _format_schema(schema) if schema else "(sin tablas descubiertas)"
        system_prompt = (
            f"Eres un generador de SQL experto para {dialect}. "
            "Devuelve exclusivamente una sentencia SELECT (o WITH ... SELECT) válida "
            f"para el dialecto {dialect}. No expliques; no uses cercas de código; "
            "no incluyas punto y coma final. Solo el SQL."
        )
        user_prompt = (
            f"Esquema disponible:\n{schema_text}\n\n"
            f"Pregunta del usuario:\n{prompt}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = await litellm_client.acompletion(messages, purpose="sql")
        content = response["choices"][0]["message"]["content"]
        return _strip_fences(str(content))

    def _execute_sql(self, engine: Engine, sql: str) -> tuple[list[dict[str, Any]], bool]:
        limit = settings.MAX_ROWS_PER_EXTRACTION
        with engine.connect() as conn:
            result = conn.execute(sa.text(sql))
            keys = list(result.keys())
            collected: list[dict[str, Any]] = []
            truncated = False
            for raw_row in result:
                if len(collected) >= limit:
                    truncated = True
                    break
                collected.append(
                    {key: _coerce_cell(raw_row[idx]) for idx, key in enumerate(keys)}
                )
            return collected, truncated

    def _error_extraction(
        self,
        *,
        connection: DataSourceConnection,
        source_type: SourceType,
        query_plan: QueryPlan,
        code: ErrorCode,
        message: str,
        technical: str | None = None,
    ) -> DataExtraction:
        return DataExtraction(
            session_id=connection.user_session_id,
            connection_id=connection.id,
            source_type=source_type,
            query_plan=query_plan,
            row_count=0,
            status="error",
            error=ExtractionError(code=code, message=message, technical_detail=technical),
        )


def _format_schema(schema: list[_TableSchema]) -> str:
    lines: list[str] = []
    for table in schema:
        cols = ", ".join(f"{name} {type_}" for name, type_ in table.columns)
        lines.append(f"- {table.name}({cols})")
    return "\n".join(lines)


def _columns_from_rows(rows: list[dict[str, Any]]) -> list[ColumnDescriptor]:
    if not rows:
        return []
    first = rows[0]
    return [
        ColumnDescriptor(name=name, type=_infer_column_type(first[name]))
        for name in first.keys()
    ]


def _classify_sqlalchemy_error(exc: SQLAlchemyError) -> tuple[ErrorCode, str]:
    text = str(exc).lower()
    orig = getattr(exc, "orig", None)
    orig_text = str(orig).lower() if orig else ""

    if isinstance(exc, ProgrammingError):
        return ErrorCode.QUERY_SYNTAX, "Error de sintaxis en la consulta SQL generada."

    if isinstance(exc, OperationalError):
        if "no such table" in orig_text or "no such table" in text:
            return ErrorCode.TARGET_NOT_FOUND, "La tabla referenciada no existe en la fuente."
        if "no such column" in orig_text or "no such column" in text:
            return ErrorCode.TARGET_NOT_FOUND, "La columna referenciada no existe en la tabla."
        if "permission denied" in orig_text or "access denied" in orig_text:
            return ErrorCode.PERMISSION_DENIED, "Permiso denegado por el motor de base de datos."
        if any(s in orig_text for s in ("connection", "could not connect", "timeout")):
            return ErrorCode.SOURCE_UNAVAILABLE, "La fuente de datos no está disponible."
        return ErrorCode.UNKNOWN, "Error operacional al ejecutar la consulta."

    return ErrorCode.UNKNOWN, "Error desconocido al ejecutar la consulta."
