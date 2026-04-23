"""Unit tests for the widget prompt builder (T104 support)."""

from __future__ import annotations

from typing import Any

from app.models.extraction import (
    ColumnDescriptor,
    DataExtraction,
    QueryPlan,
    SourceType,
)
from app.models.render_mode import UILibrary
from app.models.widget import WidgetRenderMode, WidgetType
from app.services.widget.prompt_builder import (
    PromptContext,
    RenderSettings,
    build_messages,
)


def _extraction(rows: list[dict[str, Any]]) -> DataExtraction:
    return DataExtraction(
        session_id="sess-1",
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression="SELECT 1"),
        columns=[ColumnDescriptor(name="cat", type="string"), ColumnDescriptor(name="v", type="integer")],
        rows=rows,
        row_count=len(rows),
        status="success",
    )


def test_messages_split_into_system_and_user():
    ctx = PromptContext(widget_type=WidgetType.BAR_CHART, extraction=_extraction([{"cat": "A", "v": 1}]))
    messages = build_messages(ctx)

    assert [m["role"] for m in messages] == ["system", "user"]


def test_system_prefix_is_stable_across_same_settings():
    """Stable prefix → provider prompt-caching hit (R3)."""
    ctx_a = PromptContext(widget_type=WidgetType.BAR_CHART, extraction=_extraction([{"cat": "A", "v": 1}]))
    ctx_b = PromptContext(widget_type=WidgetType.LINE_CHART, extraction=_extraction([{"cat": "B", "v": 99}]))

    system_a = build_messages(ctx_a)[0]["content"]
    system_b = build_messages(ctx_b)[0]["content"]

    assert system_a == system_b


def test_system_prefix_changes_with_ui_library():
    ctx = PromptContext(widget_type=WidgetType.TABLE, extraction=_extraction([]))
    shadcn = build_messages(ctx, RenderSettings(ui_library=UILibrary.SHADCN))[0]["content"]
    bootstrap = build_messages(ctx, RenderSettings(ui_library=UILibrary.BOOTSTRAP))[0]["content"]

    assert shadcn != bootstrap
    assert "shadcn" in shadcn.lower()
    assert "bootstrap" in bootstrap.lower()


def test_free_code_omits_component_manifest():
    ctx = PromptContext(widget_type=WidgetType.TABLE, extraction=_extraction([]))
    messages = build_messages(
        ctx, RenderSettings(render_mode=WidgetRenderMode.FREE_CODE, ui_library=None)
    )
    system = messages[0]["content"]

    assert "Component Manifest" not in system
    assert "free_code" in system


def test_user_suffix_contains_target_widget_type():
    ctx = PromptContext(widget_type=WidgetType.PIE_CHART, extraction=_extraction([{"cat": "X", "v": 1}]))
    user = build_messages(ctx)[1]["content"]

    assert "pie_chart" in user


def test_user_suffix_includes_column_and_row_count():
    rows = [{"cat": "A", "v": 1}, {"cat": "B", "v": 2}]
    ctx = PromptContext(widget_type=WidgetType.BAR_CHART, extraction=_extraction(rows))
    user = build_messages(ctx)[1]["content"]

    assert "row_count: 2" in user
    assert '"name": "cat"' in user
    assert '"type": "integer"' in user


def test_user_suffix_caps_preview_at_five_rows():
    rows = [{"cat": f"c{i}", "v": i} for i in range(20)]
    ctx = PromptContext(widget_type=WidgetType.BAR_CHART, extraction=_extraction(rows))
    user = build_messages(ctx)[1]["content"]

    assert "preview (5 rows)" in user
    assert "c4" in user
    assert "c5" not in user


def test_user_suffix_carries_extraction_and_session_ids():
    ctx = PromptContext(widget_type=WidgetType.TABLE, extraction=_extraction([]))
    user = build_messages(ctx)[1]["content"]

    assert ctx.extraction.extraction_id in user
    assert ctx.extraction.session_id in user


def test_user_intent_included_when_provided():
    ctx = PromptContext(
        widget_type=WidgetType.BAR_CHART,
        extraction=_extraction([{"cat": "A", "v": 1}]),
        user_intent="compara ventas por categoría",
    )
    user = build_messages(ctx)[1]["content"]

    assert "compara ventas por categoría" in user


def test_user_intent_omitted_when_absent():
    ctx = PromptContext(widget_type=WidgetType.BAR_CHART, extraction=_extraction([{"cat": "A", "v": 1}]))
    user = build_messages(ctx)[1]["content"]

    assert "User intent" not in user
