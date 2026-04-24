"""Contextual LLM mock router for E2E tests and offline development.

Activated by setting MOCK_LLM_RESPONSES=true. Intercepts every purpose
(sql | json | chat | widget) and returns deterministic responses that react
to the prompt content — no tokens, no network.

Rules are evaluated in order; the first matching pattern wins. Tests can
register custom rules via register_rule(purpose, pattern, response); the
defaults are sufficient for the quickstart scenarios 1-5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Literal

Purpose = Literal["sql", "json", "chat", "widget"]

# A response may be a literal string or a callable that builds one from the
# user-side prompt (last message in the chat history). Callables let us react
# to dynamic content — e.g. produce a KPI widget when the prompt asks for a total.
ResponseBuilder = Callable[[str], str]


@dataclass
class _Rule:
    pattern: re.Pattern[str]
    response: str | ResponseBuilder


@dataclass
class _PurposeRules:
    rules: list[_Rule] = field(default_factory=list)
    default: str | ResponseBuilder = ""


_DEFAULT_SQL = "SELECT id, region, amount, sold_at FROM sales LIMIT 50"

_SQL_RULES: list[tuple[str, str]] = [
    # Order matters: more specific patterns first (no-results before region/month).
    # No-results case (Escenario 3)
    (r"\b(ant[aá]rtida|antarctica|marte|mars)\b",
     "SELECT * FROM sales WHERE region = '__no_match__'"),
    # Destructive prompt → still a SELECT (read-only guard rejects server-side)
    (r"\b(borra|delete|drop|truncate)\b",
     "DELETE FROM sales"),
    # Aggregations → KPI-shaped single-row result
    (r"\btotal\b|\bsum(a)?\b|\bkpi\b",
     "SELECT SUM(amount) AS total_sales FROM sales"),
    # Sales by month → temporal/categorical
    (r"\b(mes|month|mensual)\b",
     "SELECT STRFTIME('%Y-%m', sold_at) AS sales_month, SUM(amount) AS total_sales "
     "FROM sales GROUP BY sales_month ORDER BY sales_month"),
    # Sales by region → categorical + numeric
    (r"\b(regi[oó]n|region)\b",
     "SELECT region, SUM(amount) AS total_sales FROM sales GROUP BY region"),
]


_WIDGET_TEMPLATE = (
    '{{"widget_type":"{widget_type}","bindings":{bindings},'
    '"visual_options":{{"title":"{title}"}},"code":null}}'
)


def _widget_response_for_prompt(prompt: str) -> str:
    """Return a WidgetSpec JSON matching the deterministic selector's target type.

    The prompt builder prefixes "Target widget_type: <type>" — the mock must
    honour that to produce valid bindings. Falling back to intent heuristics
    only when the marker is absent (legacy paths / tests).
    """
    lowered = prompt.lower()

    target_match = re.search(r"target widget_type:\s*(\w+)", lowered)
    target = target_match.group(1) if target_match else None

    if target == "kpi":
        return _WIDGET_TEMPLATE.format(
            widget_type="kpi",
            bindings='{"value":"total_sales","extra":{}}',
            title="Total de ventas",
        )
    if target == "bar_chart":
        if "sales_month" in lowered or "mes" in lowered or "month" in lowered:
            return _WIDGET_TEMPLATE.format(
                widget_type="bar_chart",
                bindings='{"x":"sales_month","y":"total_sales","extra":{}}',
                title="Ventas por mes",
            )
        return _WIDGET_TEMPLATE.format(
            widget_type="bar_chart",
            bindings='{"x":"region","y":"total_sales","extra":{}}',
            title="Ventas por región",
        )
    if target == "table":
        return _WIDGET_TEMPLATE.format(
            widget_type="table",
            bindings='{"columns":["region","total_sales"],"extra":{}}',
            title="Datos",
        )
    # Legacy fallback (intent-based) when no target marker is present.
    if "kpi" in lowered or "total de ventas" in lowered:
        return _WIDGET_TEMPLATE.format(
            widget_type="kpi",
            bindings='{"value":"total_sales","extra":{}}',
            title="Total de ventas",
        )
    if "mes" in lowered or "month" in lowered:
        return _WIDGET_TEMPLATE.format(
            widget_type="bar_chart",
            bindings='{"x":"sales_month","y":"total_sales","extra":{}}',
            title="Ventas por mes",
        )
    return _WIDGET_TEMPLATE.format(
        widget_type="bar_chart",
        bindings='{"x":"region","y":"total_sales","extra":{}}',
        title="Ventas por región",
    )


class MockLLMRouter:
    """Thread-safe registry of purpose → (pattern → response) rules."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_purpose: dict[Purpose, _PurposeRules] = {
            "sql": _PurposeRules(default=_DEFAULT_SQL),
            "json": _PurposeRules(default="$.products[*]"),
            "chat": _PurposeRules(default="Hola, ¿en qué puedo ayudarte?"),
            "widget": _PurposeRules(default=_widget_response_for_prompt),
        }
        self._install_defaults()

    def _install_defaults(self) -> None:
        for pattern, response in _SQL_RULES:
            self.register_rule("sql", pattern, response)

    def register_rule(
        self, purpose: Purpose, pattern: str, response: str | ResponseBuilder
    ) -> None:
        with self._lock:
            self._by_purpose[purpose].rules.append(
                _Rule(pattern=re.compile(pattern, re.IGNORECASE), response=response)
            )

    def clear_rules(self, purpose: Purpose | None = None) -> None:
        """Remove registered rules. Used by tests to isolate scenarios."""
        with self._lock:
            purposes: list[Purpose] = (
                [purpose] if purpose is not None else list(self._by_purpose.keys())
            )
            for p in purposes:
                self._by_purpose[p].rules.clear()

    def respond(self, purpose: Purpose, messages: list[dict[str, str]]) -> str:
        prompt = _extract_user_prompt(messages)
        with self._lock:
            rules = self._by_purpose[purpose]
            for rule in rules.rules:
                if rule.pattern.search(prompt):
                    return _resolve(rule.response, prompt)
            return _resolve(rules.default, prompt)


def _extract_user_prompt(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _resolve(response: str | ResponseBuilder, prompt: str) -> str:
    return response(prompt) if callable(response) else response


_router: MockLLMRouter | None = None
_router_lock = Lock()


def get_router() -> MockLLMRouter:
    global _router
    if _router is not None:
        return _router
    with _router_lock:
        if _router is None:
            _router = MockLLMRouter()
        return _router


def reset_router_for_tests() -> None:
    global _router
    with _router_lock:
        _router = None
