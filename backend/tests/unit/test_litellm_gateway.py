from unittest.mock import MagicMock, patch

import pytest

from app.models.chat import Message, Role
from app.services import litellm_client
from app.services.litellm_client import (
    LiteLLMClient,
    LiteLLMConfigurationError,
    chat_completion,
    get_client,
    reset_client_for_tests,
)
from app.services.llm_gateway import LiteLLMGateway


def _litellm_response(text: str) -> dict:
    return {"choices": [{"message": {"content": text}}]}


@pytest.fixture
def reset_singleton():
    reset_client_for_tests()
    yield
    reset_client_for_tests()


@pytest.fixture
def fake_client(reset_singleton, monkeypatch):
    client = LiteLLMClient(models={
        "sql": "provider/sql-model",
        "json": "provider/json-model",
        "chat": "provider/chat-model",
        "widget": "provider/widget-model",
    })
    monkeypatch.setattr(litellm_client, "_client", client)
    return client


# --- get_client() fail-closed behavior ---

def test_get_client_raises_without_any_credentials(reset_singleton, monkeypatch):
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(litellm_client.settings, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(litellm_client.settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(litellm_client.settings, "GEMINI_API_KEY", None)

    with pytest.raises(LiteLLMConfigurationError):
        get_client()


def test_get_client_returns_singleton(reset_singleton, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    first = get_client()
    second = get_client()
    assert first is second


# --- Routing by purpose ---

def test_chat_completion_routes_sql_purpose_to_sql_model(fake_client):
    with patch.object(litellm_client.litellm, "completion", return_value=_litellm_response("sql-out")) as mock:
        out = chat_completion([{"role": "user", "content": "hi"}], purpose="sql")
    assert out == "sql-out"
    mock.assert_called_once()
    assert mock.call_args.kwargs["model"] == "provider/sql-model"


def test_chat_completion_routes_json_purpose_to_json_model(fake_client):
    with patch.object(litellm_client.litellm, "completion", return_value=_litellm_response("json-out")) as mock:
        chat_completion([{"role": "user", "content": "hi"}], purpose="json")
    assert mock.call_args.kwargs["model"] == "provider/json-model"


def test_chat_completion_routes_chat_purpose_to_chat_model(fake_client):
    with patch.object(litellm_client.litellm, "completion", return_value=_litellm_response("chat-out")) as mock:
        chat_completion([{"role": "user", "content": "hi"}], purpose="chat")
    assert mock.call_args.kwargs["model"] == "provider/chat-model"


def test_chat_completion_forwards_messages_verbatim(fake_client):
    messages = [
        {"role": "system", "content": "you are a helper"},
        {"role": "user", "content": "hola"},
    ]
    with patch.object(litellm_client.litellm, "completion", return_value=_litellm_response("x")) as mock:
        chat_completion(messages, purpose="chat")
    assert mock.call_args.kwargs["messages"] == messages


def test_chat_completion_forwards_kwargs(fake_client):
    with patch.object(litellm_client.litellm, "completion", return_value=_litellm_response("x")) as mock:
        chat_completion([{"role": "user", "content": "hi"}], purpose="chat", temperature=0.0, max_tokens=50)
    assert mock.call_args.kwargs["temperature"] == 0.0
    assert mock.call_args.kwargs["max_tokens"] == 50


# --- LiteLLMGateway behavior ---

def test_gateway_returns_greeting_on_empty_history():
    gateway = LiteLLMGateway()
    assert gateway.complete([]) == "Hola, ¿en qué puedo ayudarte?"


def test_gateway_serializes_history_to_openai_messages(fake_client):
    history = [
        Message(role=Role.USER, content="primera"),
        Message(role=Role.ASSISTANT, content="respuesta"),
        Message(role=Role.USER, content="segunda"),
    ]
    with patch.object(litellm_client.litellm, "completion", return_value=_litellm_response("ok")) as mock:
        out = LiteLLMGateway().complete(history)

    assert out == "ok"
    called_messages = mock.call_args.kwargs["messages"]
    assert called_messages == [
        {"role": "user", "content": "primera"},
        {"role": "assistant", "content": "respuesta"},
        {"role": "user", "content": "segunda"},
    ]


def test_gateway_uses_chat_purpose(fake_client):
    history = [Message(role=Role.USER, content="hola")]
    with patch.object(litellm_client.litellm, "completion", return_value=_litellm_response("ok")) as mock:
        LiteLLMGateway().complete(history)
    assert mock.call_args.kwargs["model"] == "provider/chat-model"


def test_model_for_resolves_configured_models(fake_client):
    assert fake_client.model_for("sql") == "provider/sql-model"
    assert fake_client.model_for("json") == "provider/json-model"
    assert fake_client.model_for("chat") == "provider/chat-model"
