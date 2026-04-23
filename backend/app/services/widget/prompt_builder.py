"""Widget-generation prompt builder (T104, R3).

Assembles the LLM prompt for the Architect/Generator agent. Separates the
stable prefix (system prompt + UI library manifest) from the variable
suffix (target widget_type + data description) so providers with prompt
caching (Anthropic, OpenAI) can reuse the prefix across calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.models.extraction import DataExtraction
from app.models.render_mode import UILibrary
from app.models.widget import WidgetRenderMode, WidgetType

_PREVIEW_ROWS = 5
_MANIFESTS_DIR = Path(__file__).resolve().parent / "manifests"

_SYSTEM_PROMPT_BASE = """You are the Widget Architect for a data-analysis workspace.

Your job: given a deterministic target `widget_type` and a dataset description,
produce a strict JSON object conforming to the WidgetSpec v1 contract.

Hard requirements:
- Output ONLY the JSON object — no prose, no markdown fences.
- Every field in the contract must be present.
- `bindings` maps the dataset columns to the visual roles required by the
  target `widget_type` (e.g. x/y/series for charts, label/value for kpi).
- `code` is either null (native renderer handles the type) or a `{html, css?, js?}`
  bundle that runs inside an isolated iframe with no network access.
- Never invent columns that are not present in the data description.
- Prefer clarity and correctness over visual flourish."""


@dataclass(frozen=True)
class PromptContext:
    """Variable portion of the prompt: the request-specific context."""

    widget_type: WidgetType
    extraction: DataExtraction
    user_intent: Optional[str] = None


@lru_cache(maxsize=8)
def _load_manifest(library: UILibrary) -> str:
    manifest_path = _MANIFESTS_DIR / f"{library.value}.md"
    return manifest_path.read_text(encoding="utf-8")


def _stable_prefix(render_mode: WidgetRenderMode, ui_library: Optional[UILibrary]) -> str:
    sections = [_SYSTEM_PROMPT_BASE, f"\n\nRender mode: {render_mode.value}"]
    if render_mode == WidgetRenderMode.UI_FRAMEWORK and ui_library is not None:
        sections.append(f"\n\n## Component Manifest ({ui_library.value})\n\n")
        sections.append(_load_manifest(ui_library))
    return "".join(sections)


def _describe_dataset(extraction: DataExtraction) -> str:
    columns_json = json.dumps(
        [{"name": c.name, "type": c.type} for c in extraction.columns], ensure_ascii=False
    )
    preview_rows = extraction.rows[:_PREVIEW_ROWS]
    preview_json = json.dumps(preview_rows, ensure_ascii=False, default=str)
    return (
        f"row_count: {extraction.row_count}\n"
        f"columns: {columns_json}\n"
        f"preview ({len(preview_rows)} rows): {preview_json}"
    )


def _variable_suffix(context: PromptContext) -> str:
    parts = [
        f"Target widget_type: {context.widget_type.value}",
        f"Dataset description:\n{_describe_dataset(context.extraction)}",
    ]
    if context.user_intent:
        parts.append(f"User intent: {context.user_intent}")
    parts.append(
        f"extraction_id: {context.extraction.extraction_id}\n"
        f"session_id: {context.extraction.session_id}"
    )
    parts.append("Return the WidgetSpec JSON now.")
    return "\n\n".join(parts)


@dataclass(frozen=True)
class RenderSettings:
    render_mode: WidgetRenderMode = WidgetRenderMode.UI_FRAMEWORK
    ui_library: Optional[UILibrary] = UILibrary.SHADCN


def build_messages(
    context: PromptContext,
    settings: RenderSettings = RenderSettings(),
) -> list[dict[str, str]]:
    """Return chat messages with a stable system prefix + variable user suffix.

    The system message is identical across calls that share the same
    render_mode + ui_library, enabling provider-side prompt caching.
    """
    return [
        {"role": "system", "content": _stable_prefix(settings.render_mode, settings.ui_library)},
        {"role": "user", "content": _variable_suffix(context)},
    ]
