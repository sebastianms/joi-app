"""Unit tests for the table fallback builder (T110, R8)."""

from __future__ import annotations

from typing import Any

import pytest

from app.models.extraction import (
    ColumnDescriptor,
    DataExtraction,
    QueryPlan,
    SourceType,
)
from app.models.render_mode import UILibrary
from app.models.widget import (
    SelectionSource,
    WidgetRenderMode,
    WidgetType,
)
from app.services.widget.fallback_builder import (
    FALLBACK_MODEL_ALIAS,
    FallbackContext,
    build_table_fallback,
)


def _extraction(
    columns: list[tuple[str, str]],
    rows: list[dict[str, Any]],
    *,
    truncated: bool = False,
) -> DataExtraction:
    return DataExtraction(
        session_id="sess-123",
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression="SELECT 1"),
        columns=[ColumnDescriptor(name=n, type=t) for n, t in columns],
        rows=rows,
        row_count=len(rows),
        truncated=truncated,
        status="success",
    )


def test_fallback_produces_table_widget():
    extraction = _extraction([("id", "integer"), ("name", "string")], [{"id": 1, "name": "A"}])
    spec = build_table_fallback(extraction)

    assert spec.widget_type == WidgetType.TABLE
    assert spec.selection_source == SelectionSource.FALLBACK
    assert spec.generated_by_model == FALLBACK_MODEL_ALIAS


def test_fallback_preserves_extraction_and_session_ids():
    extraction = _extraction([("x", "integer")], [{"x": 1}])
    spec = build_table_fallback(extraction)

    assert spec.extraction_id == extraction.extraction_id
    assert spec.session_id == extraction.session_id


def test_fallback_data_reference_carries_columns_but_no_rows():
    """Rows travel via postMessage, not in the spec (contract schema)."""
    extraction = _extraction(
        [("a", "integer"), ("b", "string")],
        [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}],
    )
    spec = build_table_fallback(extraction)

    assert len(spec.data_reference.columns) == 2
    assert spec.data_reference.columns[0]["name"] == "a"
    assert spec.data_reference.rows == []


def test_fallback_inherits_truncation_flag():
    extraction = _extraction([("x", "integer")], [{"x": 1}], truncated=True)
    spec = build_table_fallback(extraction)

    assert spec.truncation_badge is True


def test_fallback_defaults_to_ui_framework_shadcn():
    extraction = _extraction([("x", "integer")], [{"x": 1}])
    spec = build_table_fallback(extraction)

    assert spec.render_mode == WidgetRenderMode.UI_FRAMEWORK
    assert spec.ui_library == UILibrary.SHADCN


def test_fallback_free_code_clears_ui_library():
    """free_code mode must not carry a ui_library (contract invariant)."""
    extraction = _extraction([("x", "integer")], [{"x": 1}])
    spec = build_table_fallback(
        extraction, FallbackContext(render_mode=WidgetRenderMode.FREE_CODE)
    )

    assert spec.render_mode == WidgetRenderMode.FREE_CODE
    assert spec.ui_library is None


def test_fallback_accepts_deterministic_selection_source():
    """When selector picks TABLE deterministically, caller can override."""
    extraction = _extraction([("name", "string")], [{"name": "A"}])
    spec = build_table_fallback(
        extraction, FallbackContext(selection_source=SelectionSource.DETERMINISTIC)
    )

    assert spec.selection_source == SelectionSource.DETERMINISTIC


def test_fallback_code_is_none_for_native_render():
    extraction = _extraction([("x", "integer")], [{"x": 1}])
    spec = build_table_fallback(extraction)

    assert spec.code is None


def test_fallback_generates_fresh_widget_id_each_call():
    extraction = _extraction([("x", "integer")], [{"x": 1}])
    a = build_table_fallback(extraction)
    b = build_table_fallback(extraction)

    assert a.widget_id != b.widget_id


def test_fallback_bindings_expose_column_order():
    extraction = _extraction(
        [("first", "string"), ("second", "integer"), ("third", "float")],
        [{"first": "x", "second": 1, "third": 1.5}],
    )
    spec = build_table_fallback(extraction)

    assert spec.bindings.extra["columns"] == ["first", "second", "third"]


def test_fallback_does_not_call_llm(monkeypatch):
    """Deckard-reviewed guarantee: fallback path is purely deterministic."""
    import app.services.litellm_client as llm

    def fail(*args, **kwargs):
        pytest.fail("fallback must not invoke LLM")

    monkeypatch.setattr(llm, "chat_completion", fail)
    monkeypatch.setattr(llm, "acompletion", fail)

    extraction = _extraction([("x", "integer")], [{"x": 1}])
    spec = build_table_fallback(extraction)

    assert spec is not None


def test_fallback_empty_extraction_still_produces_valid_spec():
    """Even with zero rows, the spec is well-formed (caller handles empty-state UX)."""
    extraction = _extraction([("x", "integer")], [])
    spec = build_table_fallback(extraction)

    assert spec.widget_type == WidgetType.TABLE
    assert spec.data_reference.columns[0]["name"] == "x"
    assert spec.truncation_badge is False
