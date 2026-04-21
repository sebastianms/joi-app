import pytest
from app.models.chat import ChatRequest, IntentType, Message, Role
from app.services.chat_manager import ChatManagerService
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService


class StubLLM(LLMGateway):
    """Test double: always returns a fixed response."""

    def complete(self, history: list[Message]) -> str:
        return "stub_response"


@pytest.fixture
def manager() -> ChatManagerService:
    return ChatManagerService(triage=TriageEngineService(), llm=StubLLM())


# --- Routing ---

def test_simple_intent_calls_llm(manager: ChatManagerService):
    response = manager.handle(ChatRequest(session_id="s1", message="hola"))
    assert response.intent_type == IntentType.SIMPLE
    assert response.response == "stub_response"


def test_complex_intent_returns_placeholder(manager: ChatManagerService):
    response = manager.handle(ChatRequest(session_id="s1", message="muéstrame las ventas por mes"))
    assert response.intent_type == IntentType.COMPLEX
    assert "Pipeline" in response.response or "agentes" in response.response


# --- Session history ---

def test_history_accumulates_messages(manager: ChatManagerService):
    manager.handle(ChatRequest(session_id="s2", message="hola"))
    manager.handle(ChatRequest(session_id="s2", message="gracias"))
    history = manager.get_history("s2")
    assert len(history) == 4  # 2 user + 2 assistant


def test_history_isolated_between_sessions(manager: ChatManagerService):
    manager.handle(ChatRequest(session_id="session-a", message="hola"))
    manager.handle(ChatRequest(session_id="session-b", message="hola"))
    assert len(manager.get_history("session-a")) == 2
    assert len(manager.get_history("session-b")) == 2


def test_history_roles_are_correct(manager: ChatManagerService):
    manager.handle(ChatRequest(session_id="s3", message="hola"))
    history = manager.get_history("s3")
    assert history[0].role == Role.USER
    assert history[1].role == Role.ASSISTANT


def test_empty_session_returns_empty_history(manager: ChatManagerService):
    assert manager.get_history("nonexistent") == []


# --- LLM receives correct context ---

class HistoryCaptureLLM(LLMGateway):
    """Test double: captures the history passed to complete()."""

    def __init__(self) -> None:
        self.received: list[Message] = []

    def complete(self, history: list[Message]) -> str:
        self.received = list(history)
        return "context_response"


def test_llm_receives_full_history_as_context():
    llm = HistoryCaptureLLM()
    manager = ChatManagerService(triage=TriageEngineService(), llm=llm)
    manager.handle(ChatRequest(session_id="ctx", message="hola"))
    manager.handle(ChatRequest(session_id="ctx", message="gracias"))
    # Second call should pass 3 messages: user1, assistant1, user2
    assert len(llm.received) == 3
    assert llm.received[-1].content == "gracias"
