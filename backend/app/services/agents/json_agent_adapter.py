"""JSON pipeline adapter: NL prompt → JSONPath → execute → DataExtraction.

Pipeline (analogous to SqlAgentAdapter, ADL-009):

    generate (LiteLLM, purpose="json")
        → execute (jsonpath-ng over in-memory JSON)
            → DataExtraction
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonpath_ng.exceptions import JSONPathError
from jsonpath_ng.ext import parse as jsonpath_parse

from app.core.config import settings
from app.models.connection import DataSourceConnection
from app.models.extraction import (
    ColumnDescriptor,
    DataExtraction,
    ErrorCode,
    ExtractionError,
    QueryPlan,
    SourceType,
)
from app.services import litellm_client

_MAX_SCHEMA_KEYS = 20
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()


def _observe_schema(data: Any, max_keys: int = _MAX_SCHEMA_KEYS) -> str:
    """Return a compact human-readable schema summary for the LLM prompt."""
    if isinstance(data, list) and data:
        sample = data[0]
        if isinstance(sample, dict):
            keys = list(sample.keys())[:max_keys]
            types = {k: type(sample[k]).__name__ for k in keys}
            suffix = f" … (+{len(sample) - max_keys} more)" if len(sample) > max_keys else ""
            return (
                "Array of objects. Sample keys: "
                + ", ".join(f"{k} ({t})" for k, t in types.items())
                + suffix
            )
        return f"Array of {type(sample).__name__}"
    if isinstance(data, dict):
        keys = list(data.keys())[:max_keys]
        return "Object with keys: " + ", ".join(keys)
    return type(data).__name__


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


def _columns_from_rows(rows: list[dict[str, Any]]) -> list[ColumnDescriptor]:
    if not rows:
        return []
    first = rows[0]
    return [
        ColumnDescriptor(name=name, type=_infer_column_type(first.get(name)))
        for name in first.keys()
    ]


class JsonAgentAdapter:
    """Generates a JSONPath expression via LiteLLM and executes it on a JSON file."""

    async def extract(
        self,
        prompt: str,
        connection: DataSourceConnection,
    ) -> DataExtraction:
        file_path = connection.file_path
        if not file_path:
            return self._error_extraction(
                connection=connection,
                query_display="",
                code=ErrorCode.SOURCE_UNAVAILABLE,
                message="La conexión JSON no tiene un archivo configurado.",
            )

        try:
            raw = Path(file_path).read_text(encoding="utf-8")
            data = json.loads(raw)
        except FileNotFoundError:
            return self._error_extraction(
                connection=connection,
                query_display="",
                code=ErrorCode.TARGET_NOT_FOUND,
                message=f"Archivo JSON no encontrado: {file_path}",
            )
        except json.JSONDecodeError as exc:
            return self._error_extraction(
                connection=connection,
                query_display="",
                code=ErrorCode.QUERY_SYNTAX,
                message="El archivo JSON no es válido.",
                technical=str(exc),
            )

        schema_summary = _observe_schema(data)
        jsonpath_expr = await self._generate_jsonpath(prompt, schema_summary)

        query_plan = QueryPlan(
            language="jsonpath",
            expression=jsonpath_expr,
            generated_by_model=settings.LLM_MODEL_JSON,
        )

        try:
            parsed = jsonpath_parse(jsonpath_expr)
            matches = [match.value for match in parsed.find(data)]
        except JSONPathError as exc:
            return self._error_extraction(
                connection=connection,
                query_display=jsonpath_expr,
                code=ErrorCode.QUERY_SYNTAX,
                message="La expresión JSONPath generada no es válida.",
                technical=str(exc),
            )

        if not matches:
            return DataExtraction(
                session_id=connection.user_session_id,
                connection_id=connection.id,
                source_type=SourceType.JSON,
                query_plan=query_plan,
                columns=[],
                rows=[],
                row_count=0,
                truncated=False,
                status="success",
            )

        limit = settings.MAX_ROWS_PER_EXTRACTION
        raw_rows = matches if isinstance(matches[0], dict) else [{"value": v} for v in matches]
        truncated = len(raw_rows) > limit
        rows = raw_rows[:limit]

        columns = _columns_from_rows(rows)
        return DataExtraction(
            session_id=connection.user_session_id,
            connection_id=connection.id,
            source_type=SourceType.JSON,
            query_plan=query_plan,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            status="success",
        )

    async def _generate_jsonpath(self, prompt: str, schema_summary: str) -> str:
        system_prompt = (
            "Eres un generador de expresiones JSONPath. "
            "Dado el esquema de un documento JSON y una pregunta en lenguaje natural, "
            "devuelve exclusivamente una expresión JSONPath válida (RFC 9535 / jsonpath-ng). "
            "No expliques; no uses cercas de código; solo la expresión."
        )
        user_prompt = (
            f"Esquema del documento:\n{schema_summary}\n\n"
            f"Pregunta del usuario:\n{prompt}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = await litellm_client.acompletion(messages, purpose="json")
        content = response["choices"][0]["message"]["content"]
        return _strip_fences(str(content))

    def _error_extraction(
        self,
        *,
        connection: DataSourceConnection,
        query_display: str,
        code: ErrorCode,
        message: str,
        technical: str | None = None,
    ) -> DataExtraction:
        return DataExtraction(
            session_id=connection.user_session_id,
            connection_id=connection.id,
            source_type=SourceType.JSON,
            query_plan=QueryPlan(language="jsonpath", expression=query_display),
            row_count=0,
            status="error",
            error=ExtractionError(code=code, message=message, technical_detail=technical),
        )
