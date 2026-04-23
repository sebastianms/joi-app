"""Unit tests for the widget generator (T111).

Mocks litellm_client.acompletion (ADL-015) — no real LLM calls.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from app.models.extraction import (
    ColumnDescriptor,
    DataExtraction,
    QueryPlan,
    SourceType,
)
from app.models.render_mode import UILibrary
from app.models.widget import (
    SelectionSource,
    WidgetErrorCode,
    WidgetRenderMode,
    WidgetType,
)
from app.services import litellm_client
from app.services.widget import generator as sut
from app.services.widget.generator import (
    GenerationRequest,
    generate_widget,
)


def _extraction(rows: list[dict[str, Any]] | None = None) -> DataExtraction:
    return DataExtraction(
        session_id="sess-xyz",
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression="SELECT 1"),
        columns=[ColumnDescriptor(name="cat", type="string"), ColumnDescriptor(name="v", type="integer")],
        rows=rows or [{"cat": "A", "v": 1}],
        row_count=len(rows) if rows is not None else 1,
        status="success",
    )


def _valid_spec_payload(extraction: DataExtraction) -> dict:
    return {
        "contract_version": "v1",
        "widget_id": "11111111-1111-1111-1111-111111111111",
        "extraction_id": extraction.extraction_id,
        "session_id": extraction.session_id,
        "render_mode": "ui_framework",
        "ui_library": "shadcn",
        "widget_type": "bar_chart",
        "selection_source": "deterministic",
        "bindings": {"x": "cat", "y": "v"},
        "data_reference": {
            "extraction_id": extraction.extraction_id,
            "columns": [{"name": "cat", "type": "string"}, {"name": "v", "type": "integer"}],
            "rows": [],
        },
        "truncation_badge": False,
        "generated_by_model": "stub",
    }


def _patch_llm(monkeypatch, content: str) -> None:
    async def fake_acompletion(messages, *, purpose, **_):
        assert purpose == "widget"
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(litellm_client, "acompletion", fake_acompletion)


# --- Happy path ---


@pytest.mark.asyncio
async def test_generate_returns_validated_spec(monkeypatch):
    extraction = _extraction()
    _patch_llm(monkeypatch, json.dumps(_valid_spec_payload(extraction)))

    result = await generate_widget(
        GenerationRequest(widget_type=WidgetType.BAR_CHART, extraction=extraction)
    )

    assert result.ok
    assert result.spec.widget_type == WidgetType.BAR_CHART
    assert result.error_code is None


@pytest.mark.asyncio
async def test_generate_strips_markdown_fences(monkeypatch):
    extraction = _extraction()
    payload = json.dumps(_valid_spec_payload(extraction))
    _patch_llm(monkeypatch, f"```json\n{payload}\n```")

    result = await generate_widget(
        GenerationRequest(widget_type=WidgetType.BAR_CHART, extraction=extraction)
    )

    assert result.ok


@pytest.mark.asyncio
async def test_generate_overrides_identity_fields(monkeypatch):
    """LLM-supplied extraction_id/session_id/render_mode are forced by the caller."""
    extraction = _extraction()
    payload = _valid_spec_payload(extraction)
    payload["extraction_id"] = "00000000-0000-0000-0000-000000000000"
    payload["session_id"] = "wrong"
    payload["render_mode"] = "free_code"
    _patch_llm(monkeypatch, json.dumps(payload))

    result = await generate_widget(
        GenerationRequest(
            widget_type=WidgetType.BAR_CHART,
            extraction=extraction,
            render_mode=WidgetRenderMode.UI_FRAMEWORK,
            ui_library=UILibrary.BOOTSTRAP,
        )
    )

    assert result.ok
    assert result.spec.extraction_id == extraction.extraction_id
    assert result.spec.session_id == extraction.session_id
    assert result.spec.render_mode == WidgetRenderMode.UI_FRAMEWORK
    assert result.spec.ui_library == UILibrary.BOOTSTRAP
    assert result.spec.selection_source == SelectionSource.DETERMINISTIC


@pytest.mark.asyncio
async def test_generate_records_model_alias(monkeypatch):
    extraction = _extraction()
    _patch_llm(monkeypatch, json.dumps(_valid_spec_payload(extraction)))
    monkeypatch.setattr(sut.settings, "LLM_MODEL_WIDGET", "test/model-x")

    result = await generate_widget(
        GenerationRequest(widget_type=WidgetType.BAR_CHART, extraction=extraction)
    )

    assert result.spec.generated_by_model == "test/model-x"
    assert result.model_alias == "test/model-x"


# --- Error paths ---


@pytest.mark.asyncio
async def test_generate_returns_spec_invalid_on_unparseable_json(monkeypatch):
    _patch_llm(monkeypatch, "not a json {{{")

    result = await generate_widget(
        GenerationRequest(widget_type=WidgetType.TABLE, extraction=_extraction())
    )

    assert not result.ok
    assert result.error_code == WidgetErrorCode.SPEC_INVALID


@pytest.mark.asyncio
async def test_generate_returns_spec_invalid_on_schema_violation(monkeypatch):
    """Missing required fields → ValidationError → SPEC_INVALID."""
    _patch_llm(monkeypatch, json.dumps({"foo": "bar"}))

    result = await generate_widget(
        GenerationRequest(widget_type=WidgetType.TABLE, extraction=_extraction())
    )

    assert not result.ok
    assert result.error_code == WidgetErrorCode.SPEC_INVALID


@pytest.mark.asyncio
async def test_generate_returns_timeout(monkeypatch):
    extraction = _extraction()

    async def slow(*_, **__):
        await asyncio.sleep(5)
        return {"choices": [{"message": {"content": "{}"}}]}

    monkeypatch.setattr(litellm_client, "acompletion", slow)
    monkeypatch.setattr(sut.settings, "WIDGET_GENERATION_TIMEOUT_SECONDS", 0)

    result = await generate_widget(
        GenerationRequest(widget_type=WidgetType.BAR_CHART, extraction=extraction)
    )

    assert not result.ok
    assert result.error_code == WidgetErrorCode.GENERATOR_TIMEOUT


@pytest.mark.asyncio
async def test_generate_returns_unknown_on_provider_error(monkeypatch):
    async def boom(*_, **__):
        raise RuntimeError("provider 503")

    monkeypatch.setattr(litellm_client, "acompletion", boom)

    result = await generate_widget(
        GenerationRequest(widget_type=WidgetType.TABLE, extraction=_extraction())
    )

    assert not result.ok
    assert result.error_code == WidgetErrorCode.UNKNOWN
    assert "provider 503" in result.error_message


@pytest.mark.asyncio
async def test_generate_records_elapsed_ms_even_on_failure(monkeypatch):
    _patch_llm(monkeypatch, "{}")

    result = await generate_widget(
        GenerationRequest(widget_type=WidgetType.TABLE, extraction=_extraction())
    )

    assert not result.ok
    assert result.generation_ms >= 0
