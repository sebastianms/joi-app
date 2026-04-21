from abc import ABC, abstractmethod
from app.models.chat import Message


class LLMGateway(ABC):
    """Abstract interface for interacting with a language model."""

    @abstractmethod
    def complete(self, history: list[Message]) -> str:
        """Generate a response given the current conversation history."""
        ...
