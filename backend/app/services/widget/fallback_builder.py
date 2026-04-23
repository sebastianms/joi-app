"""Deterministic table fallback builder (T103, R8).

Builds a `WidgetSpec` of type `table` directly from a `DataExtraction`,
without invoking the LLM. Used as the universal safety net when the
generator times out, returns an invalid spec, or when the deterministic
selector picks `table`. Also satisfies FR-009 (always-available fallback).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models.extraction import DataExtraction
from app.models.render_mode import UILibrary
from app.models.widget import (
    DataReference,
    SelectionSource,
    VisualOptions,
    WidgetBindings,
    WidgetRenderMode,
    WidgetSpec,
    WidgetType,
)

FALLBACK_MODEL_ALIAS = "deterministic"


@dataclass(frozen=True)
class FallbackContext:
    """Optional render-mode context for the fallback builder.

    Defaults match the system default (`ui_framework` + shadcn) so callers
    can invoke `build_table_fallback(extraction)` without threading config.
    """

    render_mode: WidgetRenderMode = WidgetRenderMode.UI_FRAMEWORK
    ui_library: Optional[UILibrary] = UILibrary.SHADCN
    selection_source: SelectionSource = SelectionSource.FALLBACK


_DEFAULT_CONTEXT = FallbackContext()


def build_table_fallback(
    extraction: DataExtraction,
    context: FallbackContext = _DEFAULT_CONTEXT,
) -> WidgetSpec:
    """Return a minimal table `WidgetSpec` referencing `extraction`.

    Rows are intentionally omitted from `data_reference`: the frontend
    injects them into the iframe via postMessage (per contract schema).
    """
    bindings = WidgetBindings(extra={"columns": [c.name for c in extraction.columns]})
    data_reference = DataReference(
        extraction_id=extraction.extraction_id,
        columns=[{"name": c.name, "type": c.type} for c in extraction.columns],
        rows=[],
    )
    ui_library = (
        context.ui_library if context.render_mode == WidgetRenderMode.UI_FRAMEWORK else None
    )
    return WidgetSpec(
        extraction_id=extraction.extraction_id,
        session_id=extraction.session_id,
        render_mode=context.render_mode,
        ui_library=ui_library,
        widget_type=WidgetType.TABLE,
        selection_source=context.selection_source,
        bindings=bindings,
        visual_options=VisualOptions(),
        code=None,
        data_reference=data_reference,
        truncation_badge=extraction.truncated,
        generated_by_model=FALLBACK_MODEL_ALIAS,
    )
