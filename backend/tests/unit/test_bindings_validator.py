"""Tests for the per-widget-type bindings semantic validator (T408)."""

import pytest

from app.models.widget import WidgetBindings, WidgetType
from app.services.widget.bindings_validator import (
    InvalidBindingsError,
    validate_bindings,
)


@pytest.mark.parametrize(
    "widget_type,bindings",
    [
        (WidgetType.TABLE, WidgetBindings()),
        (WidgetType.BAR_CHART, WidgetBindings(x="region", y="total")),
        (WidgetType.LINE_CHART, WidgetBindings(x="date", y="amount")),
        (WidgetType.AREA_CHART, WidgetBindings(x="date", y="amount")),
        (WidgetType.SCATTER_PLOT, WidgetBindings(x="price", y="stock")),
        (WidgetType.HEATMAP, WidgetBindings(x="month", y="region", value="total")),
        (WidgetType.PIE_CHART, WidgetBindings(label="region", value="total")),
        (WidgetType.KPI, WidgetBindings(value="total")),
    ],
)
def test_valid_bindings_pass(widget_type: WidgetType, bindings: WidgetBindings) -> None:
    validate_bindings(widget_type, bindings)


@pytest.mark.parametrize(
    "widget_type,bindings",
    [
        (WidgetType.BAR_CHART, WidgetBindings(value="total")),
        (WidgetType.BAR_CHART, WidgetBindings(x="region")),
        (WidgetType.LINE_CHART, WidgetBindings(y="amount")),
        (WidgetType.HEATMAP, WidgetBindings(x="a", y="b")),
        (WidgetType.PIE_CHART, WidgetBindings(value="total")),
        (WidgetType.KPI, WidgetBindings(label="total")),
        (WidgetType.SCATTER_PLOT, WidgetBindings()),
    ],
)
def test_invalid_bindings_raise(widget_type: WidgetType, bindings: WidgetBindings) -> None:
    with pytest.raises(InvalidBindingsError):
        validate_bindings(widget_type, bindings)


def test_empty_string_is_rejected_as_missing() -> None:
    with pytest.raises(InvalidBindingsError):
        validate_bindings(WidgetType.BAR_CHART, WidgetBindings(x="", y="total"))
