from collections import defaultdict

from app.models.chat import ChatRequest, ChatResponse, IntentType, Message, Role
from app.models.extraction import DataExtraction
from app.services.data_agent_service import DataAgentService
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService

SessionHistory = dict[str, list[Message]]


class ChatManagerService:
    """Orchestrates triage classification, LLM responses and data agent extraction per session."""

    def __init__(self, triage: TriageEngineService, llm: LLMGateway) -> None:
        self._triage = triage
        self._llm = llm
        self._history: SessionHistory = defaultdict(list)

    async def handle(
        self, request: ChatRequest, data_agent: DataAgentService
    ) -> ChatResponse:
        user_message = Message(role=Role.USER, content=request.message)
        session = self._history[request.session_id]
        session.append(user_message)

        triage_result = self._triage.classify(request.message)

        if triage_result.intent_type == IntentType.COMPLEX:
            extraction, trace = await data_agent.extract(
                request.session_id, request.message
            )
            response_text = _format_extraction_response(extraction)
            assistant_message = Message(
                role=Role.ASSISTANT,
                content=response_text,
                extraction=extraction,
                trace=trace,
            )
            session.append(assistant_message)
            return ChatResponse(
                response=response_text,
                intent_type=triage_result.intent_type,
                extraction=extraction,
                trace=trace,
            )

        response_text = self._llm.complete(list(session))
        assistant_message = Message(role=Role.ASSISTANT, content=response_text)
        session.append(assistant_message)
        return ChatResponse(
            response=response_text,
            intent_type=triage_result.intent_type,
        )

    def get_history(self, session_id: str) -> list[Message]:
        return list(self._history[session_id])


def _format_extraction_response(extraction: DataExtraction) -> str:
    if extraction.status == "success":
        if extraction.truncated:
            return (
                f"Encontré {extraction.row_count} filas (resultado truncado al "
                f"límite configurado)."
            )
        return f"Encontré {extraction.row_count} filas."
    if extraction.error is not None:
        return extraction.error.message
    return "No pude completar la extracción."
