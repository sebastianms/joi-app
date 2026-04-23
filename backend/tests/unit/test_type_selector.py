"""Unit tests for the deterministic widget type selector (T108, R1)."""

from __future__ import annotations

from typing import Any

from app.models.extraction import (
    ColumnDescriptor,
    DataExtraction,
    QueryPlan,
    SourceType,
)
from app.models.widget import WidgetType
from app.services.widget.type_selector import select_widget_type


def _extraction(
    columns: list[tuple[str, str]],
    rows: list[dict[str, Any]],
) -> DataExtraction:
    return DataExtraction(
        session_id="s-1",
        connection_id="c-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression="SELECT 1"),
        columns=[ColumnDescriptor(name=n, type=t) for n, t in columns],
        rows=rows,
        row_count=len(rows),
        status="success",
    )


def test_kpi_single_row_single_numeric():
    extraction = _extraction([("total", "integer")], [{"total": 42}])
    assert select_widget_type(extraction) == WidgetType.KPI


def test_line_chart_datetime_and_numeric():
    rows = [{"ts": f"2026-01-{d:02d}", "value": d} for d in range(1, 11)]
    extraction = _extraction([("ts", "datetime"), ("value", "integer")], rows)
    assert select_widget_type(extraction) == WidgetType.LINE_CHART


def test_line_chart_falls_back_to_table_when_over_500_points():
    rows = [{"ts": f"2026-01-{i:04d}", "value": i} for i in range(1, 502)]
    extraction = _extraction([("ts", "datetime"), ("value", "integer")], rows)
    assert select_widget_type(extraction) == WidgetType.TABLE


def test_heatmap_two_small_categoricals_plus_numeric():
    rows = [
        {"region": r, "product": p, "sales": s}
        for r, p, s in [
            ("N", "A", 10),
            ("N", "B", 20),
            ("S", "A", 15),
            ("S", "B", 25),
        ]
    ]
    extraction = _extraction(
        [("region", "string"), ("product", "string"), ("sales", "integer")], rows
    )
    assert select_widget_type(extraction) == WidgetType.HEATMAP


def test_bar_chart_single_categorical_plus_numeric():
    rows = [
        {"product": "A", "sales": 10},
        {"product": "B", "sales": 20},
        {"product": "C", "sales": 30},
    ]
    extraction = _extraction([("product", "string"), ("sales", "integer")], rows)
    assert select_widget_type(extraction) == WidgetType.BAR_CHART


def test_scatter_two_numerics_no_strings():
    rows = [{"x": i, "y": i * 2} for i in range(10)]
    extraction = _extraction([("x", "float"), ("y", "float")], rows)
    assert select_widget_type(extraction) == WidgetType.SCATTER_PLOT


def test_table_fallback_for_only_strings():
    rows = [
        {"name": "Alice", "role": "dev"},
        {"name": "Bob", "role": "qa"},
    ]
    extraction = _extraction([("name", "string"), ("role", "string")], rows)
    # Both categoricals but no numeric → heatmap/bar don't match → fallback
    assert select_widget_type(extraction) == WidgetType.TABLE


def test_table_fallback_for_categorical_over_50_uniques():
    rows = [{"code": f"code_{i}", "qty": i} for i in range(60)]
    extraction = _extraction([("code", "string"), ("qty", "integer")], rows)
    # 60 unique categoricals exceed _MAX_CAT_UNIQUE_BAR → bar rule rejected
    assert select_widget_type(extraction) == WidgetType.TABLE


def test_empty_rows_return_table_not_chart():
    extraction = _extraction([("product", "string"), ("sales", "integer")], [])
    # row_count=0: selector does NOT emit empty-state itself; caller handles that.
    # With no rows, no categorical has ≥2 uniques → bar rule rejected → table.
    assert select_widget_type(extraction) == WidgetType.TABLE


def test_kpi_not_emitted_when_multiple_numerics_single_row():
    extraction = _extraction(
        [("a", "integer"), ("b", "integer")], [{"a": 1, "b": 2}]
    )
    # 2 numerics + no strings → scatter_plot wins over KPI (KPI requires exactly 1 numeric)
    assert select_widget_type(extraction) == WidgetType.SCATTER_PLOT


def test_heatmap_wins_over_bar_when_two_categoricals_present():
    rows = [
        {"r": "N", "p": "A", "v": 10},
        {"r": "N", "p": "B", "v": 15},
        {"r": "S", "p": "A", "v": 20},
        {"r": "S", "p": "B", "v": 25},
    ]
    extraction = _extraction(
        [("r", "string"), ("p", "string"), ("v", "integer")], rows
    )
    assert select_widget_type(extraction) == WidgetType.HEATMAP


def test_datetime_without_numeric_falls_through():
    rows = [{"ts": "2026-01-01", "label": "x"}, {"ts": "2026-01-02", "label": "y"}]
    extraction = _extraction([("ts", "datetime"), ("label", "string")], rows)
    assert select_widget_type(extraction) == WidgetType.TABLE
