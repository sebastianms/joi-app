"""Unit tests for the widget preference pass in TriageEngineService (T202, R10, FR-006a)."""

from __future__ import annotations

import pytest

from app.models.chat import IntentType
from app.models.widget import WidgetType
from app.services.triage_engine import TriageEngineService


@pytest.fixture
def engine() -> TriageEngineService:
    return TriageEngineService()


# ---------------------------------------------------------------------------
# Happy path: each of the 8 widget types detected from preference phrases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phrase,expected", [
    # bar_chart — Spanish + English variants
    ("muéstramelo como barras", WidgetType.BAR_CHART),
    ("prefiero un gráfico de barras", WidgetType.BAR_CHART),
    ("show it as a bar chart", WidgetType.BAR_CHART),
    # table
    ("prefiero verlo como tabla", WidgetType.TABLE),
    ("show me a table", WidgetType.TABLE),
    # line_chart
    ("quiero un gráfico de líneas", WidgetType.LINE_CHART),
    ("show it as a line chart", WidgetType.LINE_CHART),
    ("muéstrame las series temporales", WidgetType.LINE_CHART),
    # pie_chart
    ("mejor como pastel", WidgetType.PIE_CHART),
    ("muéstramelo como torta", WidgetType.PIE_CHART),
    ("use a pie chart", WidgetType.PIE_CHART),
    ("use a donut", WidgetType.PIE_CHART),
    # kpi
    ("quiero ver el kpi", WidgetType.KPI),
    ("muéstrame el indicador", WidgetType.KPI),
    ("necesito la métrica", WidgetType.KPI),
    # scatter_plot
    ("muéstramelo como scatter plot", WidgetType.SCATTER_PLOT),
    ("prefiero dispersión", WidgetType.SCATTER_PLOT),
    ("show as scatter", WidgetType.SCATTER_PLOT),
    # heatmap
    ("muéstramelo como heatmap", WidgetType.HEATMAP),
    ("prefiero mapa de calor", WidgetType.HEATMAP),
    # area_chart
    ("muéstramelo como área", WidgetType.AREA_CHART),
    ("show as area chart", WidgetType.AREA_CHART),
    ("prefiero gráfico de área", WidgetType.AREA_CHART),
])
def test_detects_single_preference(
    engine: TriageEngineService, phrase: str, expected: WidgetType
) -> None:
    result = engine.classify(phrase, has_prior_extraction=True)
    assert result.preferred_widget_type == expected


# ---------------------------------------------------------------------------
# Multiple matches → no preference (conservative, R10)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phrase", [
    "prefiero barras o tabla",
    "mapa de calor o scatter",
    "bar chart or table",
])
def test_multiple_matches_returns_no_preference(
    engine: TriageEngineService, phrase: str
) -> None:
    result = engine.classify(phrase, has_prior_extraction=True)
    assert result.preferred_widget_type is None


# ---------------------------------------------------------------------------
# No prior extraction → single preference phrase stays SIMPLE (no route change)
# Phrases must not contain complex keywords (e.g. "tabla" IS a complex keyword).
# ---------------------------------------------------------------------------

def test_preference_phrase_without_prior_extraction_stays_simple(
    engine: TriageEngineService,
) -> None:
    # "scatter" not in _COMPLEX_KEYWORDS; only the widget-preference regex picks it up
    result = engine.classify("prefiero scatter", has_prior_extraction=False)
    assert result.intent_type == IntentType.SIMPLE
    assert result.preferred_widget_type is None


# ---------------------------------------------------------------------------
# Route when preference is detected via prior extraction (phrase has no data keywords)
# ---------------------------------------------------------------------------

def test_preference_with_prior_extraction_routes_to_widget_preference(
    engine: TriageEngineService,
) -> None:
    # "scatter" not in _COMPLEX_KEYWORDS → goes to second pass
    result = engine.classify("prefiero scatter", has_prior_extraction=True)
    assert result.intent_type == IntentType.COMPLEX
    assert result.suggested_route == "widget_preference"
    assert result.confidence == 0.9


# ---------------------------------------------------------------------------
# Complex keyword + preference → preferred_widget_type is set
# ---------------------------------------------------------------------------

def test_complex_keyword_with_preference_sets_preferred_type(
    engine: TriageEngineService,
) -> None:
    result = engine.classify("muéstrame los datos como gráfico de barras")
    assert result.intent_type == IntentType.COMPLEX
    assert result.preferred_widget_type == WidgetType.BAR_CHART
    assert result.suggested_route == "agent_pipeline"


def test_complex_keyword_without_preference_has_none(
    engine: TriageEngineService,
) -> None:
    result = engine.classify("muéstrame los datos de ventas")
    assert result.intent_type == IntentType.COMPLEX
    assert result.preferred_widget_type is None


# ---------------------------------------------------------------------------
# Backward-compatibility: existing classify(message) without has_prior_extraction
# ---------------------------------------------------------------------------

def test_classify_without_prior_extraction_flag_defaults_to_false(
    engine: TriageEngineService,
) -> None:
    result = engine.classify("prefiero barras")
    assert result.intent_type == IntentType.SIMPLE
    assert result.preferred_widget_type is None
