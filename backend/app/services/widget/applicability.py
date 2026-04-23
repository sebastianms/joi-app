"""Widget applicability validator (T102, R1, FR-006a).

Given a candidate `WidgetType` and a `DataExtraction`, decide whether the pair
is compatible. Used when the user expresses a preference (US2) to verify that
the requested type fits the data before invoking the generator; falls back to
proposing valid alternatives otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.extraction import DataExtraction
from app.models.widget import WidgetType
from app.services.widget._column_utils import (
    datetime_columns,
    numeric_columns,
    small_categoricals,
    string_columns,
)

_MAX_LINE_POINTS = 500
_MAX_CAT_UNIQUE_BAR = 50
_MAX_CAT_UNIQUE_HEATMAP = 30
_MAX_CAT_UNIQUE_PIE = 10
_MAX_SCATTER_POINTS = 2000
_MIN_CAT_UNIQUE = 2


@dataclass(frozen=True)
class ApplicabilityResult:
    compatible: bool
    reason: str
    alternatives: list[WidgetType] = field(default_factory=list)


def _all_positive_numeric(rows: list[dict], column: str) -> bool:
    for row in rows:
        value = row.get(column)
        if value is not None and value < 0:
            return False
    return True


def _check_table(extraction: DataExtraction) -> ApplicabilityResult:
    if extraction.row_count == 0:
        return ApplicabilityResult(False, "no hay filas para mostrar")
    return ApplicabilityResult(True, "tabla siempre aplicable")


def _check_bar(extraction: DataExtraction) -> ApplicabilityResult:
    numerics = numeric_columns(extraction.columns)
    if not numerics:
        return ApplicabilityResult(False, "bar_chart requiere al menos una columna numérica")
    strings = string_columns(extraction.columns)
    cats = small_categoricals(extraction.rows, strings, _MIN_CAT_UNIQUE, _MAX_CAT_UNIQUE_BAR)
    if not cats:
        return ApplicabilityResult(
            False,
            f"bar_chart requiere una categórica con {_MIN_CAT_UNIQUE}–{_MAX_CAT_UNIQUE_BAR} valores únicos",
        )
    return ApplicabilityResult(True, "categórica pequeña + numérica presentes")


def _check_line(extraction: DataExtraction) -> ApplicabilityResult:
    if not datetime_columns(extraction.columns):
        return ApplicabilityResult(False, "line_chart requiere una columna temporal")
    if not numeric_columns(extraction.columns):
        return ApplicabilityResult(False, "line_chart requiere una columna numérica")
    if extraction.row_count > _MAX_LINE_POINTS:
        return ApplicabilityResult(
            False, f"line_chart soporta hasta {_MAX_LINE_POINTS} puntos ({extraction.row_count} recibidos)"
        )
    return ApplicabilityResult(True, "temporal + numérica presentes")


def _check_pie(extraction: DataExtraction) -> ApplicabilityResult:
    numerics = numeric_columns(extraction.columns)
    if not numerics:
        return ApplicabilityResult(False, "pie_chart requiere una columna numérica")
    strings = string_columns(extraction.columns)
    cats = small_categoricals(extraction.rows, strings, _MIN_CAT_UNIQUE, _MAX_CAT_UNIQUE_PIE)
    if not cats:
        return ApplicabilityResult(
            False,
            f"pie_chart requiere una categórica con {_MIN_CAT_UNIQUE}–{_MAX_CAT_UNIQUE_PIE} valores únicos",
        )
    if not _all_positive_numeric(extraction.rows, numerics[0].name):
        return ApplicabilityResult(False, "pie_chart no admite valores negativos")
    return ApplicabilityResult(True, "categórica pequeña + numérica positiva")


def _check_kpi(extraction: DataExtraction) -> ApplicabilityResult:
    if extraction.row_count != 1:
        return ApplicabilityResult(False, "kpi requiere exactamente una fila")
    if len(numeric_columns(extraction.columns)) != 1:
        return ApplicabilityResult(False, "kpi requiere exactamente una columna numérica")
    return ApplicabilityResult(True, "una fila con una numérica")


def _check_scatter(extraction: DataExtraction) -> ApplicabilityResult:
    if len(numeric_columns(extraction.columns)) < 2:
        return ApplicabilityResult(False, "scatter_plot requiere al menos dos numéricas")
    if extraction.row_count > _MAX_SCATTER_POINTS:
        return ApplicabilityResult(
            False, f"scatter_plot soporta hasta {_MAX_SCATTER_POINTS} puntos"
        )
    return ApplicabilityResult(True, "dos numéricas disponibles")


def _check_heatmap(extraction: DataExtraction) -> ApplicabilityResult:
    if not numeric_columns(extraction.columns):
        return ApplicabilityResult(False, "heatmap requiere una columna numérica")
    strings = string_columns(extraction.columns)
    small = small_categoricals(extraction.rows, strings, _MIN_CAT_UNIQUE, _MAX_CAT_UNIQUE_HEATMAP)
    if len(small) < 2:
        return ApplicabilityResult(
            False,
            f"heatmap requiere dos categóricas con {_MIN_CAT_UNIQUE}–{_MAX_CAT_UNIQUE_HEATMAP} valores únicos",
        )
    return ApplicabilityResult(True, "dos categóricas pequeñas + numérica")


def _check_area(extraction: DataExtraction) -> ApplicabilityResult:
    if not datetime_columns(extraction.columns):
        return ApplicabilityResult(False, "area_chart requiere una columna temporal")
    if not numeric_columns(extraction.columns):
        return ApplicabilityResult(False, "area_chart requiere una columna numérica")
    return ApplicabilityResult(True, "temporal + numérica presentes")


_CHECKS = {
    WidgetType.TABLE: _check_table,
    WidgetType.BAR_CHART: _check_bar,
    WidgetType.LINE_CHART: _check_line,
    WidgetType.PIE_CHART: _check_pie,
    WidgetType.KPI: _check_kpi,
    WidgetType.SCATTER_PLOT: _check_scatter,
    WidgetType.HEATMAP: _check_heatmap,
    WidgetType.AREA_CHART: _check_area,
}


def check_applicability(
    widget_type: WidgetType, extraction: DataExtraction
) -> ApplicabilityResult:
    """Validate that `widget_type` fits `extraction`.

    When incompatible, the result includes alternative types that would fit
    the same data, always offering `TABLE` last as universal fallback.
    """
    result = _CHECKS[widget_type](extraction)
    if result.compatible:
        return result

    alternatives = [
        t for t in WidgetType if t != widget_type and _CHECKS[t](extraction).compatible
    ]
    if WidgetType.TABLE in alternatives:
        alternatives.remove(WidgetType.TABLE)
        alternatives.append(WidgetType.TABLE)
    return ApplicabilityResult(False, result.reason, alternatives)
