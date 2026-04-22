import pytest
from pydantic import ValidationError

from app.models.extraction import (
    AgentTrace,
    ColumnDescriptor,
    DataExtraction,
    ErrorCode,
    ExtractionError,
    QueryPlan,
    SourceType,
)


def build_query_plan(expression: str = "SELECT 1") -> QueryPlan:
    return QueryPlan(language="sql", expression=expression)


def build_successful_extraction(**overrides) -> DataExtraction:
    defaults = dict(
        session_id="session-1",
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=build_query_plan(),
        columns=[ColumnDescriptor(name="id", type="integer")],
        rows=[{"id": 1}],
        row_count=1,
        status="success",
    )
    defaults.update(overrides)
    return DataExtraction(**defaults)


def build_error_extraction(code: ErrorCode = ErrorCode.TIMEOUT, **overrides) -> DataExtraction:
    defaults = dict(
        session_id="session-1",
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=build_query_plan(),
        row_count=0,
        status="error",
        error=ExtractionError(code=code, message="Error de prueba"),
    )
    defaults.update(overrides)
    return DataExtraction(**defaults)


def test_successful_extraction_has_contract_version():
    extraction = build_successful_extraction()

    assert extraction.contract_version == "v1"


def test_error_extraction_requires_error_field():
    with pytest.raises(ValidationError):
        DataExtraction(
            session_id="s",
            connection_id="c",
            source_type=SourceType.SQL_SQLITE,
            query_plan=build_query_plan(),
            row_count=0,
            status="error",
            # error omitido intencionalmente
        )


def test_success_extraction_rejects_error_field():
    with pytest.raises(ValidationError):
        DataExtraction(
            session_id="s",
            connection_id="c",
            source_type=SourceType.SQL_SQLITE,
            query_plan=build_query_plan(),
            row_count=1,
            rows=[{"id": 1}],
            status="success",
            error=ExtractionError(code=ErrorCode.UNKNOWN, message="no debería estar"),
        )


def test_json_serialization_includes_contract_version():
    extraction = build_successful_extraction()

    data = extraction.model_dump(mode="json")

    assert data["contract_version"] == "v1"
    assert data["status"] == "success"
    assert data["error"] is None


def test_error_extraction_serializes_error_code():
    extraction = build_error_extraction(code=ErrorCode.SECURITY_REJECTION)

    data = extraction.model_dump(mode="json")

    assert data["status"] == "error"
    assert data["error"]["code"] == "SECURITY_REJECTION"


def test_agent_trace_defaults_to_collapsed():
    extraction = build_successful_extraction()
    trace = AgentTrace(
        extraction_id=extraction.extraction_id,
        pipeline="sql",
        query_display="SELECT 1",
    )

    assert trace.collapsed is True
    assert trace.security_rejection is False


def test_agent_trace_security_rejection_flag():
    extraction = build_error_extraction(code=ErrorCode.SECURITY_REJECTION)
    trace = AgentTrace(
        extraction_id=extraction.extraction_id,
        pipeline="sql",
        query_display="DELETE FROM sales",
        security_rejection=True,
    )

    assert trace.security_rejection is True


def test_column_descriptor_validates_type():
    with pytest.raises(ValidationError):
        ColumnDescriptor(name="col", type="invalid_type")
