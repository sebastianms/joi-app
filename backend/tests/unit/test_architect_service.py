"""Unit tests for the architect service (T112)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.models.extraction import (
    ColumnDescriptor,
    DataExtraction,
    QueryPlan,
    SourceType,
)
from app.models.widget import (
    SelectionSource,
    WidgetErrorCode,
    WidgetType,
)
from app.services import litellm_client
from app.services.widget import architect_service as architect_mod
from app.services.widget.architect_service import (
    ArchitectRequest,
    build_widget,
)


def _extraction(
    columns: list[tuple[str, str]], rows: list[dict[str, Any]]
) -> DataExtraction:
    return DataExtraction(
        session_id="sess-1",
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression="SELECT 1"),
        columns=[ColumnDescriptor(name=n, type=t) for n, t in columns],
        rows=rows,
        row_count=len(rows),
        status="success",
    )


def _valid_payload(extraction: DataExtraction, widget_type: str) -> dict:
    return {
        "contract_version": "v1",
        "widget_id": "22222222-2222-2222-2222-222222222222",
        "extraction_id": extraction.extraction_id,
        "session_id": extraction.session_id,
        "render_mode": "ui_framework",
        "ui_library": "shadcn",
        "widget_type": widget_type,
        "selection_source": "deterministic",
        "bindings": {"x": "cat", "y": "v"},
        "data_reference": {
            "extraction_id": extraction.extraction_id,
            "columns": [{"name": c.name, "type": c.type} for c in extraction.columns],
            "row_count": extraction.row_count,
        },
        "truncation_badge": False,
        "generated_by_model": "stub",
    }


def _patch_llm(monkeypatch, content: str) -> None:
    async def fake_acompletion(messages, *, purpose, **_):
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(litellm_client, "acompletion", fake_acompletion)


# --- Empty / preference branches ---


@pytest.mark.asyncio
async def test_empty_extraction_returns_no_widget():
    extraction = _extraction([("x", "integer")], [])
    outcome = await build_widget(ArchitectRequest(extraction=extraction))

    assert outcome.spec is None
    assert outcome.trace is None
    assert outcome.preference_hint is None


@pytest.mark.asyncio
async def test_preferred_type_incompatible_returns_hint_without_widget():
    """KPI requested on multi-row data → hint with alternatives, no spec."""
    extraction = _extraction([("v", "integer")], [{"v": 1}, {"v": 2}])
    outcome = await build_widget(
        ArchitectRequest(extraction=extraction, preferred_widget_type=WidgetType.KPI)
    )

    assert outcome.spec is None
    assert outcome.preference_hint is not None
    assert outcome.preference_hint.requested == WidgetType.KPI
    assert WidgetType.TABLE in outcome.preference_hint.alternatives


# --- TABLE path: deterministic, no LLM ---


@pytest.mark.asyncio
async def test_deterministic_table_does_not_call_llm(monkeypatch):
    async def fail(*_, **__):
        pytest.fail("TABLE path must not invoke LLM")

    monkeypatch.setattr(litellm_client, "acompletion", fail)

    extraction = _extraction([("name", "string")], [{"name": "Alice"}, {"name": "Bob"}])
    outcome = await build_widget(ArchitectRequest(extraction=extraction))

    assert outcome.spec is not None
    assert outcome.spec.widget_type == WidgetType.TABLE
    assert outcome.spec.selection_source == SelectionSource.DETERMINISTIC
    assert outcome.trace.status == "success"
    assert outcome.trace.generated_by_model == "deterministic"


@pytest.mark.asyncio
async def test_preferred_table_accepted(monkeypatch):
    async def fail(*_, **__):
        pytest.fail("TABLE path must not invoke LLM")

    monkeypatch.setattr(litellm_client, "acompletion", fail)

    extraction = _extraction([("cat", "string"), ("v", "integer")], [{"cat": "A", "v": 1}])
    outcome = await build_widget(
        ArchitectRequest(extraction=extraction, preferred_widget_type=WidgetType.TABLE)
    )

    assert outcome.spec.widget_type == WidgetType.TABLE
    assert outcome.spec.selection_source == SelectionSource.USER_PREFERENCE


# --- Chart path: happy ---


@pytest.mark.asyncio
async def test_chart_success_emits_success_trace(monkeypatch):
    extraction = _extraction(
        [("cat", "string"), ("v", "integer")],
        [{"cat": "A", "v": 1}, {"cat": "B", "v": 2}],
    )
    _patch_llm(monkeypatch, json.dumps(_valid_payload(extraction, "bar_chart")))

    outcome = await build_widget(ArchitectRequest(extraction=extraction))

    assert outcome.spec.widget_type == WidgetType.BAR_CHART
    assert outcome.spec.selection_source == SelectionSource.DETERMINISTIC
    assert outcome.trace.status == "success"
    assert outcome.trace.widget_type_attempted == WidgetType.BAR_CHART


@pytest.mark.asyncio
async def test_preferred_chart_compatible_uses_user_preference_source(monkeypatch):
    extraction = _extraction(
        [("cat", "string"), ("v", "integer")],
        [{"cat": "A", "v": 1}, {"cat": "B", "v": 2}],
    )
    _patch_llm(monkeypatch, json.dumps(_valid_payload(extraction, "pie_chart")))

    outcome = await build_widget(
        ArchitectRequest(extraction=extraction, preferred_widget_type=WidgetType.PIE_CHART)
    )

    assert outcome.spec.widget_type == WidgetType.PIE_CHART
    assert outcome.spec.selection_source == SelectionSource.USER_PREFERENCE


# --- Chart path: failures fall back ---


@pytest.mark.asyncio
async def test_generator_timeout_falls_back_to_table(monkeypatch):
    extraction = _extraction(
        [("cat", "string"), ("v", "integer")],
        [{"cat": "A", "v": 1}, {"cat": "B", "v": 2}],
    )

    async def fake_generate(*_, **__):
        from app.services.widget.generator import GenerationResult
        return GenerationResult(
            spec=None,
            error_code=WidgetErrorCode.GENERATOR_TIMEOUT,
            error_message="timeout",
            generation_ms=8000,
            model_alias="stub",
        )

    monkeypatch.setattr(architect_mod, "generate_widget", fake_generate)

    outcome = await build_widget(ArchitectRequest(extraction=extraction))

    assert outcome.spec.widget_type == WidgetType.TABLE
    assert outcome.spec.selection_source == SelectionSource.FALLBACK
    assert outcome.trace.status == "fallback"
    assert outcome.trace.error_code == WidgetErrorCode.GENERATOR_TIMEOUT
    assert outcome.trace.widget_type_attempted == WidgetType.BAR_CHART


@pytest.mark.asyncio
async def test_invalid_spec_falls_back_to_table(monkeypatch):
    extraction = _extraction(
        [("cat", "string"), ("v", "integer")],
        [{"cat": "A", "v": 1}, {"cat": "B", "v": 2}],
    )
    _patch_llm(monkeypatch, "not json at all")

    outcome = await build_widget(ArchitectRequest(extraction=extraction))

    assert outcome.spec.widget_type == WidgetType.TABLE
    assert outcome.spec.selection_source == SelectionSource.FALLBACK
    assert outcome.trace.status == "fallback"
    assert outcome.trace.error_code == WidgetErrorCode.SPEC_INVALID


@pytest.mark.asyncio
async def test_trace_records_model_and_timing_on_success(monkeypatch):
    extraction = _extraction(
        [("cat", "string"), ("v", "integer")],
        [{"cat": "A", "v": 1}, {"cat": "B", "v": 2}],
    )
    _patch_llm(monkeypatch, json.dumps(_valid_payload(extraction, "bar_chart")))

    outcome = await build_widget(ArchitectRequest(extraction=extraction))

    assert outcome.trace.generated_by_model  # non-empty
    assert outcome.trace.generation_ms >= 0
