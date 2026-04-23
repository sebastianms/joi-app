"""Per-widget-type bindings semantic validator (T408).

Pydantic only validates the SHAPE of `WidgetBindings` (all fields optional),
not that the combination is semantically usable by the renderer. For example,
a `bar_chart` with `bindings={"value": "total"}` passes Pydantic but cannot
be rendered (needs `x` and `y`).

This validator runs AFTER Pydantic parsing and BEFORE the spec leaves the
generator, so invalid specs turn into `SPEC_INVALID` errors that the
architect service catches and converts into a table fallback (FR-009).

Required bindings per widget type come from the frontend renderers
(`frontend/src/lib/widget-runtime/renderers/*.tsx`).
"""

from __future__ import annotations

from app.models.widget import WidgetBindings, WidgetType


REQUIRED_BINDINGS: dict[WidgetType, tuple[str, ...]] = {
    WidgetType.TABLE: (),
    WidgetType.BAR_CHART: ("x", "y"),
    WidgetType.LINE_CHART: ("x", "y"),
    WidgetType.AREA_CHART: ("x", "y"),
    WidgetType.SCATTER_PLOT: ("x", "y"),
    WidgetType.HEATMAP: ("x", "y", "value"),
    WidgetType.PIE_CHART: ("label", "value"),
    WidgetType.KPI: ("value",),
}


class InvalidBindingsError(ValueError):
    """Raised when a WidgetSpec's bindings are missing fields required by its type."""


def validate_bindings(widget_type: WidgetType, bindings: WidgetBindings) -> None:
    required = REQUIRED_BINDINGS.get(widget_type, ())
    missing = [name for name in required if getattr(bindings, name) in (None, "")]
    if missing:
        raise InvalidBindingsError(
            f"{widget_type.value} requires bindings {required}, missing: {missing}"
        )
