"""Widget Architect/Generator (T105, R3, R6).

Invokes the LLM via the LiteLLM gateway with `Purpose="widget"`, parses the
JSON response into a `WidgetSpec`, and returns either a validated spec or a
structured error. Does NOT touch the fallback path — the caller (architect
service) decides whether to fall back when an error is returned.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Optional

from pydantic import ValidationError

from app.core.config import settings
from app.models.extraction import DataExtraction
from app.models.render_mode import UILibrary
from app.models.widget import (
    SelectionSource,
    WidgetErrorCode,
    WidgetRenderMode,
    WidgetSpec,
    WidgetType,
)
from app.services import litellm_client
from app.services.widget.prompt_builder import (
    PromptContext,
    RenderSettings,
    build_messages,
)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text).strip()


@dataclass(frozen=True)
class GenerationRequest:
    widget_type: WidgetType
    extraction: DataExtraction
    render_mode: WidgetRenderMode = WidgetRenderMode.UI_FRAMEWORK
    ui_library: Optional[UILibrary] = UILibrary.SHADCN
    user_intent: Optional[str] = None


@dataclass(frozen=True)
class GenerationResult:
    spec: Optional[WidgetSpec]
    error_code: Optional[WidgetErrorCode]
    error_message: Optional[str]
    generation_ms: int
    model_alias: str

    @property
    def ok(self) -> bool:
        return self.spec is not None


def _override_spec_invariants(spec: WidgetSpec, request: GenerationRequest) -> WidgetSpec:
    """Force fields the LLM must not decide (IDs, source, render mode).

    The model is allowed to produce `bindings`, `visual_options`, `code`,
    but identity fields and render-mode context come from the caller. The
    `data_reference.extraction_id` and `row_count` are also forced so the
    widget never references a phantom dataset.
    """
    data_reference = spec.data_reference.model_copy(
        update={
            "extraction_id": request.extraction.extraction_id,
            "row_count": request.extraction.row_count,
        }
    )
    return spec.model_copy(
        update={
            "extraction_id": request.extraction.extraction_id,
            "session_id": request.extraction.session_id,
            "render_mode": request.render_mode,
            "ui_library": request.ui_library if request.render_mode == WidgetRenderMode.UI_FRAMEWORK else None,
            "selection_source": SelectionSource.DETERMINISTIC,
            "widget_type": request.widget_type,
            "truncation_badge": request.extraction.truncated,
            "data_reference": data_reference,
        }
    )


async def _call_llm(request: GenerationRequest) -> str:
    messages = build_messages(
        PromptContext(
            widget_type=request.widget_type,
            extraction=request.extraction,
            user_intent=request.user_intent,
        ),
        RenderSettings(render_mode=request.render_mode, ui_library=request.ui_library),
    )
    response = await litellm_client.acompletion(messages, purpose="widget")
    return str(response["choices"][0]["message"]["content"])


def _parse_spec(raw: str, request: GenerationRequest) -> WidgetSpec:
    payload = json.loads(_strip_fences(raw))
    spec = WidgetSpec.model_validate(payload)
    return _override_spec_invariants(spec, request)


async def generate_widget(request: GenerationRequest) -> GenerationResult:
    """Invoke the LLM and return a validated `WidgetSpec` or a structured error."""
    model_alias = settings.LLM_MODEL_WIDGET
    start = asyncio.get_event_loop().time()

    def elapsed_ms() -> int:
        return int((asyncio.get_event_loop().time() - start) * 1000)

    try:
        raw = await asyncio.wait_for(
            _call_llm(request), timeout=settings.WIDGET_GENERATION_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        return GenerationResult(
            spec=None,
            error_code=WidgetErrorCode.GENERATOR_TIMEOUT,
            error_message=f"LLM exceeded {settings.WIDGET_GENERATION_TIMEOUT_SECONDS}s",
            generation_ms=elapsed_ms(),
            model_alias=model_alias,
        )
    except Exception as exc:  # provider errors, network, etc.
        return GenerationResult(
            spec=None,
            error_code=WidgetErrorCode.UNKNOWN,
            error_message=str(exc),
            generation_ms=elapsed_ms(),
            model_alias=model_alias,
        )

    try:
        spec = _parse_spec(raw, request)
    except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
        return GenerationResult(
            spec=None,
            error_code=WidgetErrorCode.SPEC_INVALID,
            error_message=str(exc),
            generation_ms=elapsed_ms(),
            model_alias=model_alias,
        )

    spec = spec.model_copy(update={"generated_by_model": model_alias})
    return GenerationResult(
        spec=spec,
        error_code=None,
        error_message=None,
        generation_ms=elapsed_ms(),
        model_alias=model_alias,
    )
