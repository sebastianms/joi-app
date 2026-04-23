"""Widget Architect orchestration service (T106).

Facade that coordinates the deterministic selector (R1), the LLM generator
(T105), and the table fallback (R8). Always emits a `WidgetGenerationTrace`
so the UI trace block and observability surface can display outcome + latency.

Behavior:
- Empty extraction (row_count == 0) → no widget, no trace (caller shows empty state).
- User preference incompatible with data → no widget, preference_hint returned.
- TABLE target → deterministic fallback (no LLM).
- Chart target → LLM generator; on any failure, fallback to table.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

_logger = logging.getLogger(__name__)

from app.models.extraction import DataExtraction
from app.models.render_mode import UILibrary
from app.models.widget import (
    SelectionSource,
    WidgetErrorCode,
    WidgetGenerationTrace,
    WidgetRenderMode,
    WidgetSpec,
    WidgetType,
)
from app.services.widget.applicability import check_applicability
from app.services.widget.fallback_builder import (
    FALLBACK_MODEL_ALIAS,
    FallbackContext,
    build_table_fallback,
)
from app.services.widget.generator import (
    GenerationRequest,
    GenerationResult,
    generate_widget,
)
from app.services.widget.type_selector import select_widget_type


@dataclass(frozen=True)
class ArchitectRequest:
    extraction: DataExtraction
    render_mode: WidgetRenderMode = WidgetRenderMode.UI_FRAMEWORK
    ui_library: Optional[UILibrary] = UILibrary.SHADCN
    user_intent: Optional[str] = None
    preferred_widget_type: Optional[WidgetType] = None


@dataclass(frozen=True)
class PreferenceHint:
    """Caller-facing signal that the user's preference did not fit the data."""

    requested: WidgetType
    reason: str
    alternatives: list[WidgetType]


@dataclass(frozen=True)
class ArchitectOutcome:
    spec: Optional[WidgetSpec]
    trace: Optional[WidgetGenerationTrace]
    preference_hint: Optional[PreferenceHint] = None


def _fallback_with_source(
    request: ArchitectRequest, selection_source: SelectionSource
) -> WidgetSpec:
    context = FallbackContext(
        render_mode=request.render_mode,
        ui_library=request.ui_library,
        selection_source=selection_source,
    )
    return build_table_fallback(request.extraction, context)


@dataclass(frozen=True)
class _SuccessTraceInfo:
    widget_type: WidgetType
    generation_ms: int
    model_alias: str


def _trace_success(spec: WidgetSpec, info: _SuccessTraceInfo) -> WidgetGenerationTrace:
    return WidgetGenerationTrace(
        extraction_id=spec.extraction_id,
        widget_id=spec.widget_id,
        widget_type_attempted=info.widget_type,
        status="success",
        message=f"widget {info.widget_type.value} generado",
        generated_by_model=info.model_alias,
        generation_ms=info.generation_ms,
    )


@dataclass(frozen=True)
class _FallbackTraceInfo:
    attempted: WidgetType
    generation_ms: int
    error_code: WidgetErrorCode


def _trace_fallback(spec: WidgetSpec, info: _FallbackTraceInfo) -> WidgetGenerationTrace:
    return WidgetGenerationTrace(
        extraction_id=spec.extraction_id,
        widget_id=spec.widget_id,
        widget_type_attempted=info.attempted,
        status="fallback",
        message=f"generador falló ({info.error_code.value}): tabla como respaldo",
        generated_by_model=FALLBACK_MODEL_ALIAS,
        generation_ms=info.generation_ms,
        error_code=info.error_code,
    )


def _trace_deterministic_table(spec: WidgetSpec) -> WidgetGenerationTrace:
    return WidgetGenerationTrace(
        extraction_id=spec.extraction_id,
        widget_id=spec.widget_id,
        widget_type_attempted=WidgetType.TABLE,
        status="success",
        message="tabla determinística (sin LLM)",
        generated_by_model=FALLBACK_MODEL_ALIAS,
        generation_ms=0,
    )


def _resolve_widget_type(
    request: ArchitectRequest,
) -> tuple[WidgetType, SelectionSource, Optional[PreferenceHint]]:
    """Return (widget_type, selection_source, preference_hint_if_incompatible)."""
    if request.preferred_widget_type is None:
        return select_widget_type(request.extraction), SelectionSource.DETERMINISTIC, None

    result = check_applicability(request.preferred_widget_type, request.extraction)
    if result.compatible:
        return request.preferred_widget_type, SelectionSource.USER_PREFERENCE, None

    hint = PreferenceHint(
        requested=request.preferred_widget_type,
        reason=result.reason,
        alternatives=result.alternatives,
    )
    return WidgetType.TABLE, SelectionSource.USER_PREFERENCE, hint


async def _generate_chart(
    request: ArchitectRequest, widget_type: WidgetType
) -> GenerationResult:
    return await generate_widget(
        GenerationRequest(
            widget_type=widget_type,
            extraction=request.extraction,
            render_mode=request.render_mode,
            ui_library=request.ui_library,
            user_intent=request.user_intent,
        )
    )


async def build_widget(request: ArchitectRequest) -> ArchitectOutcome:
    """Orchestrate selection → generation → (fallback if needed)."""
    if request.extraction.row_count == 0:
        return ArchitectOutcome(spec=None, trace=None)

    try:
        return await _build_widget_inner(request)
    except Exception as exc:
        _logger.exception("Unexpected error in build_widget: %s", exc)
        try:
            fallback_spec = _fallback_with_source(request, SelectionSource.FALLBACK)
        except Exception:
            return ArchitectOutcome(spec=None, trace=None)
        trace = _trace_fallback(
            fallback_spec,
            _FallbackTraceInfo(
                attempted=WidgetType.TABLE,
                generation_ms=0,
                error_code=WidgetErrorCode.UNKNOWN,
            ),
        )
        return ArchitectOutcome(spec=fallback_spec, trace=trace)


async def _build_widget_inner(request: ArchitectRequest) -> ArchitectOutcome:
    widget_type, selection_source, hint = _resolve_widget_type(request)
    if hint is not None:
        return ArchitectOutcome(spec=None, trace=None, preference_hint=hint)

    if widget_type == WidgetType.TABLE:
        spec = _fallback_with_source(request, selection_source)
        return ArchitectOutcome(spec=spec, trace=_trace_deterministic_table(spec))

    result = await _generate_chart(request, widget_type)
    if result.ok:
        spec = result.spec.model_copy(update={"selection_source": selection_source})
        return ArchitectOutcome(
            spec=spec,
            trace=_trace_success(
                spec,
                _SuccessTraceInfo(
                    widget_type=widget_type,
                    generation_ms=result.generation_ms,
                    model_alias=result.model_alias,
                ),
            ),
        )

    fallback_spec = _fallback_with_source(request, SelectionSource.FALLBACK)
    info = _FallbackTraceInfo(
        attempted=widget_type,
        generation_ms=result.generation_ms,
        error_code=result.error_code or WidgetErrorCode.UNKNOWN,
    )
    return ArchitectOutcome(spec=fallback_spec, trace=_trace_fallback(fallback_spec, info))
