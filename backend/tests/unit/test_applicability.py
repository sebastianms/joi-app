"""Unit tests for the applicability validator (T109, R1)."""

from __future__ import annotations

from typing import Any

from app.models.extraction import (
    ColumnDescriptor,
    DataExtraction,
    QueryPlan,
    SourceType,
)
from app.models.widget import WidgetType
from app.services.widget.applicability import check_applicability


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


def test_table_compatible_when_rows_present():
    extraction = _extraction([("name", "string")], [{"name": "Alice"}])
    result = check_applicability(WidgetType.TABLE, extraction)
    assert result.compatible


def test_table_incompatible_when_empty():
    extraction = _extraction([("name", "string")], [])
    result = check_applicability(WidgetType.TABLE, extraction)
    assert not result.compatible


def test_kpi_compatible_with_single_numeric_row():
    extraction = _extraction([("total", "integer")], [{"total": 99}])
    result = check_applicability(WidgetType.KPI, extraction)
    assert result.compatible


def test_kpi_incompatible_with_multiple_rows():
    rows = [{"total": 1}, {"total": 2}]
    extraction = _extraction([("total", "integer")], rows)
    result = check_applicability(WidgetType.KPI, extraction)
    assert not result.compatible
    assert "una fila" in result.reason


def test_heatmap_incompatible_with_kpi_data_offers_alternatives():
    """KPI shape (1 row, 1 numeric) cannot be a heatmap; alternatives suggested."""
    extraction = _extraction([("total", "integer")], [{"total": 42}])
    result = check_applicability(WidgetType.HEATMAP, extraction)
    assert not result.compatible
    assert WidgetType.KPI in result.alternatives
    assert WidgetType.TABLE == result.alternatives[-1]


def test_pie_rejects_negative_numeric():
    rows = [{"category": "A", "value": -10}, {"category": "B", "value": 20}]
    extraction = _extraction([("category", "string"), ("value", "integer")], rows)
    result = check_applicability(WidgetType.PIE_CHART, extraction)
    assert not result.compatible
    assert "negativos" in result.reason


def test_pie_accepts_small_categorical_with_positive_numeric():
    rows = [{"cat": "A", "v": 10}, {"cat": "B", "v": 20}, {"cat": "C", "v": 30}]
    extraction = _extraction([("cat", "string"), ("v", "integer")], rows)
    result = check_applicability(WidgetType.PIE_CHART, extraction)
    assert result.compatible


def test_line_rejects_when_over_500_points():
    rows = [{"ts": f"2026-01-{i:04d}", "v": i} for i in range(501)]
    extraction = _extraction([("ts", "datetime"), ("v", "integer")], rows)
    result = check_applicability(WidgetType.LINE_CHART, extraction)
    assert not result.compatible


def test_line_accepts_datetime_and_numeric():
    rows = [{"ts": f"2026-01-{i:02d}", "v": i} for i in range(1, 11)]
    extraction = _extraction([("ts", "datetime"), ("v", "integer")], rows)
    result = check_applicability(WidgetType.LINE_CHART, extraction)
    assert result.compatible


def test_scatter_requires_two_numerics():
    extraction = _extraction([("x", "float")], [{"x": 1.0}, {"x": 2.0}])
    result = check_applicability(WidgetType.SCATTER_PLOT, extraction)
    assert not result.compatible
    assert "dos numéricas" in result.reason


def test_heatmap_requires_two_small_categoricals():
    rows = [{"r": "N", "v": 10}, {"r": "S", "v": 20}]
    extraction = _extraction([("r", "string"), ("v", "integer")], rows)
    result = check_applicability(WidgetType.HEATMAP, extraction)
    assert not result.compatible


def test_bar_rejects_when_categorical_too_large():
    rows = [{"code": f"c{i}", "qty": i} for i in range(60)]
    extraction = _extraction([("code", "string"), ("qty", "integer")], rows)
    result = check_applicability(WidgetType.BAR_CHART, extraction)
    assert not result.compatible


def test_alternatives_exclude_the_requested_type():
    extraction = _extraction([("total", "integer")], [{"total": 42}])
    result = check_applicability(WidgetType.HEATMAP, extraction)
    assert WidgetType.HEATMAP not in result.alternatives


def test_area_requires_temporal_and_numeric():
    rows = [{"label": "x", "v": 1}, {"label": "y", "v": 2}]
    extraction = _extraction([("label", "string"), ("v", "integer")], rows)
    result = check_applicability(WidgetType.AREA_CHART, extraction)
    assert not result.compatible
    assert "temporal" in result.reason
