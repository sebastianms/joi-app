"""Widget Architect/Generator (T105, R3, R6).

Invokes the LLM via the LiteLLM gateway with `Purpose="widget"`, parses the
JSON response into a `WidgetSpec`, and returns either a validated spec or a
structured error. Does NOT touch the fallback path — the caller (architect
service) decides whether to fall back when an error is returned.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import pydantic
from pydantic import ValidationError

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.models.extraction import DataExtraction
from app.models.render_mode import UILibrary
from app.models.widget import (
    DataReference,
    SelectionSource,
    WidgetBindings,
    WidgetCode,
    WidgetErrorCode,
    WidgetRenderMode,
    WidgetSpec,
    WidgetType,
    VisualOptions,
)
from app.services import litellm_client
from app.services.widget.prompt_builder import (
    PromptContext,
    RenderSettings,
    build_messages,
)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class _LLMPayload(pydantic.BaseModel):
    """Fields the LLM is responsible for producing.

    The caller owns identity + provenance fields and applies them via
    _override_spec_invariants after validation. Keeping this model narrow
    avoids SPEC_INVALID errors when the model correctly omits fields it
    must not invent.
    """

    widget_type: WidgetType
    bindings: WidgetBindings
    visual_options: Optional[VisualOptions] = None
    code: Optional[WidgetCode] = None


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
    llm = _LLMPayload.model_validate(payload)
    return _build_spec(llm, request)


def _build_spec(llm: _LLMPayload, request: GenerationRequest) -> WidgetSpec:
    """Merge LLM-owned fields with caller-owned identity/provenance fields."""
    data_reference = DataReference(
        extraction_id=request.extraction.extraction_id,
        columns=[c.model_dump() for c in request.extraction.columns],
        row_count=request.extraction.row_count,
    )
    return WidgetSpec(
        extraction_id=request.extraction.extraction_id,
        session_id=request.extraction.session_id,
        render_mode=request.render_mode,
        ui_library=request.ui_library if request.render_mode == WidgetRenderMode.UI_FRAMEWORK else None,
        widget_type=request.widget_type,
        selection_source=SelectionSource.DETERMINISTIC,
        bindings=llm.bindings,
        visual_options=llm.visual_options,
        code=llm.code,
        data_reference=data_reference,
        truncation_badge=request.extraction.truncated,
        generated_by_model="",  # filled by caller after success
    )


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
        logger.warning("SPEC_INVALID — raw LLM output:\n%s\n\nError: %s", raw, exc)
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
