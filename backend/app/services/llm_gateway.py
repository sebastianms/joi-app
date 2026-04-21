from abc import ABC, abstractmethod

from app.models.chat import Message


class LLMGateway(ABC):
    """Abstract interface for interacting with a language model."""

    @abstractmethod
    def complete(self, history: list[Message]) -> str:
        """Generate a response given the current conversation history."""
        ...


class EchoLLMGateway(LLMGateway):
    """Stub LLM implementation used until a real provider is wired in."""

    _PLACEHOLDER_PREFIX = "Echo:"

    def complete(self, history: list[Message]) -> str:
        if not history:
            return "Hola, ¿en qué puedo ayudarte?"
        last_message = history[-1]
        return f"{self._PLACEHOLDER_PREFIX} {last_message.content}"