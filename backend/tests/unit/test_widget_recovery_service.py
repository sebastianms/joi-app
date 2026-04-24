"""Unit tests for WidgetRecoveryService (T080, US4)."""

from __future__ import annotations

import pytest

from app.models.chat import WidgetSummary
from app.services.widget_recovery_service import WidgetRecoveryService


class _StubWidget:
    def __init__(self, id: str, display_name: str | None) -> None:
        self.id = id
        self.display_name = display_name


class _StubRepo:
    def __init__(self, widgets: list[_StubWidget]) -> None:
        self._widgets = widgets

    async def list_saved(self, session_id: str) -> list[_StubWidget]:
        return list(self._widgets)


def _service(widgets: list[_StubWidget]) -> WidgetRecoveryService:
    return WidgetRecoveryService(_StubRepo(widgets))


@pytest.mark.asyncio
async def test_empty_saved_list_returns_no_match():
    svc = _service([])
    match, candidates = await svc.find("s1", "ventas Q3")
    assert match is None
    assert candidates == []


@pytest.mark.asyncio
async def test_unique_close_match_returns_direct_match():
    svc = _service([_StubWidget("w1", "Ventas Q3"), _StubWidget("w2", "Costos anuales")])
    match, candidates = await svc.find("s1", "ventas q3")
    assert match is not None
    assert match.id == "w1"
    assert candidates == []


@pytest.mark.asyncio
async def test_multiple_close_matches_returns_candidates():
    svc = _service([
        _StubWidget("w1", "Ventas enero"),
        _StubWidget("w2", "Ventas febrero"),
        _StubWidget("w3", "Costos anuales"),
    ])
    match, candidates = await svc.find("s1", "ventas")
    assert match is None
    assert len(candidates) >= 2
    ids = {c.id for c in candidates}
    assert "w1" in ids
    assert "w2" in ids


@pytest.mark.asyncio
async def test_no_match_above_cutoff_returns_empty():
    svc = _service([_StubWidget("w1", "Facturación trimestral")])
    match, candidates = await svc.find("s1", "xyzabc")
    assert match is None
    assert candidates == []


@pytest.mark.asyncio
async def test_widget_without_display_name_uses_id():
    svc = _service([_StubWidget("widget-abc-123", None)])
    match, candidates = await svc.find("s1", "widget-abc-123")
    assert match is not None
    assert match.display_name == "widget-abc-123"


@pytest.mark.asyncio
async def test_returns_widget_summary_type():
    svc = _service([_StubWidget("w1", "Reporte mensual")])
    match, _ = await svc.find("s1", "reporte mensual")
    assert isinstance(match, WidgetSummary)
