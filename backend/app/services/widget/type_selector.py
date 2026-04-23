"""Deterministic widget type selector (FR-004, R1).

Maps a DataExtraction to a WidgetType using column-shape heuristics.
Zero LLM calls — auditable and unit-testable. Falls back to `table` when
no chart pattern matches.
"""

from __future__ import annotations

from app.models.extraction import DataExtraction
from app.models.widget import WidgetType
from app.services.widget._column_utils import (
    datetime_columns,
    numeric_columns,
    small_categoricals,
    string_columns,
)


def _exclude_date_like(columns: list) -> list:
    """Filter out string columns whose names look like date/time fields."""
    return [c for c in columns if c.name.lower() not in _DATE_LIKE_NAMES]

_MAX_LINE_POINTS = 500
_MAX_CAT_UNIQUE_BAR = 50
_MAX_CAT_UNIQUE_HEATMAP = 30
_MIN_CAT_UNIQUE = 2
# Heatmap needs enough cells to be meaningful (rows × 2 axes).
_MIN_HEATMAP_ROWS = 4

# Patterns that suggest a string column is a date/time value, not a true category.
_DATE_LIKE_NAMES = frozenset({
    "date", "fecha", "time", "tiempo", "sold_at", "created_at", "updated_at",
    "timestamp", "datetime", "day", "month", "year", "week",
})


def select_widget_type(extraction: DataExtraction) -> WidgetType:
    """Apply R1 selection rules in priority order.

    Returns the first matching type; `table` is the universal fallback.
    Callers handle `row_count == 0` separately as an empty state.
    """
    columns = extraction.columns
    rows = extraction.rows
    row_count = extraction.row_count

    numerics = numeric_columns(columns)
    datetimes = datetime_columns(columns)
    strings = string_columns(columns)

    if row_count == 1 and len(numerics) == 1:
        return WidgetType.KPI

    if datetimes and numerics and row_count <= _MAX_LINE_POINTS:
        return WidgetType.LINE_CHART

    true_strings = _exclude_date_like(strings)
    heatmap_cats = small_categoricals(rows, true_strings, _MIN_CAT_UNIQUE, _MAX_CAT_UNIQUE_HEATMAP)
    if len(heatmap_cats) >= 2 and numerics and row_count >= _MIN_HEATMAP_ROWS:
        return WidgetType.HEATMAP

    bar_cats = small_categoricals(rows, true_strings, _MIN_CAT_UNIQUE, _MAX_CAT_UNIQUE_BAR)
    if bar_cats and numerics:
        return WidgetType.BAR_CHART

    if len(numerics) >= 2 and not strings:
        return WidgetType.SCATTER_PLOT

    return WidgetType.TABLE
