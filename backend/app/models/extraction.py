import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class SourceType(str, Enum):
    SQL_POSTGRESQL = "SQL_POSTGRESQL"
    SQL_MYSQL = "SQL_MYSQL"
    SQL_SQLITE = "SQL_SQLITE"
    JSON = "JSON"


class ErrorCode(str, Enum):
    NO_CONNECTION = "NO_CONNECTION"
    SECURITY_REJECTION = "SECURITY_REJECTION"
    QUERY_SYNTAX = "QUERY_SYNTAX"
    TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TIMEOUT = "TIMEOUT"
    AMBIGUOUS_PROMPT = "AMBIGUOUS_PROMPT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class ColumnDescriptor(BaseModel):
    name: str = Field(min_length=1)
    type: Literal["string", "integer", "float", "boolean", "datetime", "null", "unknown"]


class QueryPlan(BaseModel):
    language: Literal["sql", "jsonpath"]
    expression: str
    parameters: Optional[dict[str, Any]] = None
    generated_by_model: Optional[str] = None


class ExtractionError(BaseModel):
    code: ErrorCode
    message: str
    technical_detail: Optional[str] = None


class DataExtraction(BaseModel):
    contract_version: Literal["v1"] = "v1"
    extraction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(min_length=1)
    connection_id: str = Field(min_length=1)
    source_type: SourceType
    query_plan: QueryPlan
    columns: list[ColumnDescriptor] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = Field(ge=0)
    truncated: bool = False
    status: Literal["success", "error"]
    error: Optional[ExtractionError] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_error_presence(self) -> "DataExtraction":
        if self.status == "error" and self.error is None:
            raise ValueError("error must be set when status='error'")
        if self.status == "success" and self.error is not None:
            raise ValueError("error must be None when status='success'")
        return self


class AgentTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    extraction_id: str
    pipeline: Literal["sql", "json"]
    query_display: str
    preview_rows: list[dict[str, Any]] = Field(default_factory=list)
    preview_columns: list[ColumnDescriptor] = Field(default_factory=list)
    security_rejection: bool = False
    collapsed: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
