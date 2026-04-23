"""Tests for the contextual MockLLMRouter used in E2E and offline development."""

from __future__ import annotations

import pytest

from app.services.mock_llm_router import MockLLMRouter, reset_router_for_tests


@pytest.fixture(autouse=True)
def _reset_router():
    reset_router_for_tests()
    yield
    reset_router_for_tests()


def _prompt(content: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": content}]


# --- SQL purpose: contextual rules react to keyword patterns ------------------

def test_sql_prompt_asking_for_total_returns_aggregation():
    router = MockLLMRouter()
    sql = router.respond("sql", _prompt("dame el total de ventas"))
    assert "SUM(amount)" in sql


def test_sql_prompt_asking_by_month_returns_temporal_aggregation():
    router = MockLLMRouter()
    sql = router.respond("sql", _prompt("ventas por mes"))
    assert "STRFTIME" in sql and "sales_month" in sql


def test_sql_prompt_asking_by_region_returns_categorical_aggregation():
    router = MockLLMRouter()
    sql = router.respond("sql", _prompt("ventas por región"))
    assert "region" in sql.lower() and "GROUP BY" in sql


def test_sql_prompt_without_match_returns_default():
    router = MockLLMRouter()
    sql = router.respond("sql", _prompt("hola"))
    assert "SELECT" in sql and "sales" in sql


def test_destructive_prompt_returns_non_select_for_guard_tests():
    router = MockLLMRouter()
    sql = router.respond("sql", _prompt("borra todos los registros"))
    assert sql.strip().upper().startswith("DELETE")


# --- Widget purpose: response varies with prompt shape ------------------------

def test_widget_prompt_mentioning_total_returns_kpi_spec():
    router = MockLLMRouter()
    spec_json = router.respond("widget", _prompt("total de ventas"))
    assert '"widget_type":"kpi"' in spec_json


def test_widget_prompt_mentioning_region_returns_bar_chart_spec():
    router = MockLLMRouter()
    spec_json = router.respond("widget", _prompt("ventas por region"))
    assert '"widget_type":"bar_chart"' in spec_json
    assert '"x":"region"' in spec_json


def test_widget_default_returns_valid_bar_chart_spec():
    router = MockLLMRouter()
    spec_json = router.respond("widget", _prompt("algo random"))
    assert '"widget_type":"bar_chart"' in spec_json


# --- Other purposes -----------------------------------------------------------

def test_chat_purpose_returns_greeting_by_default():
    router = MockLLMRouter()
    assert "ayudarte" in router.respond("chat", _prompt("hola"))


def test_json_purpose_returns_jsonpath_by_default():
    router = MockLLMRouter()
    assert router.respond("json", _prompt("extrae productos")) == "$.products[*]"


# --- Rule registration and clearing -------------------------------------------

def test_register_rule_overrides_default():
    router = MockLLMRouter()
    router.register_rule("sql", r"\bcustom\b", "SELECT 1 AS custom")
    assert router.respond("sql", _prompt("custom query")) == "SELECT 1 AS custom"


def test_clear_rules_restores_default_behavior():
    router = MockLLMRouter()
    router.register_rule("sql", r"\bcustom\b", "SELECT 1 AS custom")
    router.clear_rules("sql")
    # Custom rule gone; default SELECT is returned
    response = router.respond("sql", _prompt("custom query"))
    assert response != "SELECT 1 AS custom"
    assert "SELECT" in response


def test_register_callable_response_receives_prompt():
    router = MockLLMRouter()
    router.register_rule("chat", r"\becho\b", lambda p: f"you said: {p}")
    assert router.respond("chat", _prompt("echo test")) == "you said: echo test"
