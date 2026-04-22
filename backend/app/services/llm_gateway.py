from abc import ABC, abstractmethod

from app.models.chat import Message
from app.services.litellm_client import chat_completion


class LLMGateway(ABC):
    """Abstract interface for interacting with a language model."""

    @abstractmethod
    def complete(self, history: list[Message]) -> str:
        """Generate a response given the current conversation history."""
        ...


class LiteLLMGateway(LLMGateway):
    """Chat gateway backed by the LiteLLM singleton (purpose='chat')."""

    def complete(self, history: list[Message]) -> str:
        if not history:
            return "Hola, ¿en qué puedo ayudarte?"
        messages = [{"role": m.role.value, "content": m.content} for m in history]
        return chat_completion(messages, purpose="chat")
