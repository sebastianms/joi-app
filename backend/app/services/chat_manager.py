from collections import defaultdict

from app.models.chat import ChatRequest, ChatResponse, IntentType, Message, Role
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService

_COMPLEX_INTENT_PLACEHOLDER = (
    "Entendido. Voy a analizar tus datos para generar la visualización solicitada. "
    "(Pipeline de agentes aún no implementado en esta fase.)"
)

SessionHistory = dict[str, list[Message]]


class ChatManagerService:
    """Orchestrates triage classification and LLM response generation per session."""

    def __init__(self, triage: TriageEngineService, llm: LLMGateway) -> None:
        self._triage = triage
        self._llm = llm
        self._history: SessionHistory = defaultdict(list)

    def handle(self, request: ChatRequest) -> ChatResponse:
        user_message = Message(role=Role.USER, content=request.message)
        session = self._history[request.session_id]
        session.append(user_message)

        triage_result = self._triage.classify(request.message)

        if triage_result.intent_type == IntentType.COMPLEX:
            response_text = _COMPLEX_INTENT_PLACEHOLDER
        else:
            response_text = self._llm.complete(list(session))

        assistant_message = Message(role=Role.ASSISTANT, content=response_text)
        session.append(assistant_message)

        return ChatResponse(
            response=response_text,
            intent_type=triage_result.intent_type,
        )

    def get_history(self, session_id: str) -> list[Message]:
        return list(self._history[session_id])
