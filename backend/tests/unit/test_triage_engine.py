import pytest
from app.models.chat import IntentType
from app.services.triage_engine import TriageEngineService


@pytest.fixture
def engine() -> TriageEngineService:
    return TriageEngineService()


# --- Simple intent: greeting patterns ---

def test_classifies_hola_as_simple(engine: TriageEngineService):
    result = engine.classify("hola")
    assert result.intent_type == IntentType.SIMPLE
    assert result.suggested_route == "direct_response"
    assert result.confidence == 1.0


def test_classifies_hello_as_simple(engine: TriageEngineService):
    result = engine.classify("Hello!")
    assert result.intent_type == IntentType.SIMPLE


def test_classifies_gracias_as_simple(engine: TriageEngineService):
    result = engine.classify("gracias")
    assert result.intent_type == IntentType.SIMPLE
    assert result.matched_pattern is not None


def test_classifies_ok_as_simple(engine: TriageEngineService):
    result = engine.classify("ok")
    assert result.intent_type == IntentType.SIMPLE


def test_classifies_bye_as_simple(engine: TriageEngineService):
    result = engine.classify("bye")
    assert result.intent_type == IntentType.SIMPLE


# --- Complex intent: data/visualization keywords ---

def test_classifies_show_data_as_complex(engine: TriageEngineService):
    result = engine.classify("muéstrame las ventas por mes")
    assert result.intent_type == IntentType.COMPLEX
    assert result.suggested_route == "agent_pipeline"
    assert result.confidence == 0.9


def test_classifies_chart_request_as_complex(engine: TriageEngineService):
    result = engine.classify("dame una gráfica de usuarios activos")
    assert result.intent_type == IntentType.COMPLEX


def test_classifies_query_as_complex(engine: TriageEngineService):
    result = engine.classify("consulta los datos del último trimestre")
    assert result.intent_type == IntentType.COMPLEX


def test_classifies_report_as_complex(engine: TriageEngineService):
    result = engine.classify("genera un reporte de ventas")
    assert result.intent_type == IntentType.COMPLEX


def test_classifies_top_as_complex(engine: TriageEngineService):
    result = engine.classify("top 10 productos más vendidos")
    assert result.intent_type == IntentType.COMPLEX


# --- Fallback: unknown/ambiguous message ---

def test_unknown_message_falls_back_to_simple(engine: TriageEngineService):
    result = engine.classify("¿puedes ayudarme con algo?")
    assert result.intent_type == IntentType.SIMPLE
    assert result.confidence == 0.6
    assert result.suggested_route == "direct_response"


# --- Boundary: edge inputs ---

def test_empty_message_falls_back_to_simple(engine: TriageEngineService):
    result = engine.classify("")
    assert result.intent_type == IntentType.SIMPLE


def test_long_message_with_complex_keyword(engine: TriageEngineService):
    long_msg = "necesito que " + "analices " * 20 + "los datos de ventas del año pasado"
    result = engine.classify(long_msg)
    assert result.intent_type == IntentType.COMPLEX
