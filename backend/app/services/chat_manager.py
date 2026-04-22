from collections import defaultdict
import logging

from app.models.chat import ChatRequest, ChatResponse, IntentType, Message, Role
from app.models.extraction import DataExtraction, AgentTrace, ErrorCode, ExtractionError, QueryPlan, SourceType
from app.services.data_agent_service import DataAgentService
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService

_logger = logging.getLogger(__name__)

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
            try:
                extraction, trace = await data_agent.extract(
                    request.session_id, request.message
                )
            except Exception as exc:
                _logger.exception("Unexpected error in data_agent.extract: %s", exc)
                extraction = _unknown_error_extraction(request.session_id)
                trace = _unknown_error_trace(extraction)
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


_ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.NO_CONNECTION: (
        "No hay una fuente de datos activa para esta sesión. "
        "Configura una conexión en /setup antes de continuar."
    ),
    ErrorCode.SECURITY_REJECTION: (
        "La consulta fue bloqueada por el guard de solo lectura. "
        "Solo se permiten consultas SELECT."
    ),
    ErrorCode.QUERY_SYNTAX: (
        "La consulta generada contiene un error de sintaxis. "
        "Intenta reformular tu pregunta."
    ),
    ErrorCode.TARGET_NOT_FOUND: (
        "No encontré la tabla o columna referenciada en tu consulta. "
        "Verifica que el nombre sea correcto."
    ),
    ErrorCode.PERMISSION_DENIED: (
        "No tengo permiso para acceder a esa parte de la fuente de datos."
    ),
    ErrorCode.TIMEOUT: (
        "La consulta tardó demasiado y fue cancelada. "
        "Intenta una consulta más específica o con menos datos."
    ),
    ErrorCode.SOURCE_UNAVAILABLE: (
        "La fuente de datos no está disponible en este momento. "
        "Verifica la conexión e inténtalo de nuevo."
    ),
    ErrorCode.AMBIGUOUS_PROMPT: (
        "No pude interpretar tu pregunta con certeza. "
        "¿Puedes reformularla con más detalle?"
    ),
    ErrorCode.UNKNOWN: (
        "Ocurrió un error inesperado al procesar tu consulta. Inténtalo de nuevo."
    ),
}


def _format_extraction_response(extraction: DataExtraction) -> str:
    if extraction.status == "success":
        if extraction.row_count == 0:
            return "La consulta no devolvió filas."
        if extraction.truncated:
            return (
                f"Encontré {extraction.row_count} filas (resultado truncado al "
                f"límite configurado)."
            )
        return f"Encontré {extraction.row_count} filas."
    if extraction.error is not None:
        return _ERROR_MESSAGES.get(extraction.error.code, extraction.error.message)
    return "No pude completar la extracción."


def _unknown_error_extraction(session_id: str) -> DataExtraction:
    return DataExtraction(
        session_id=session_id,
        connection_id="__unknown__",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression=""),
        row_count=0,
        status="error",
        error=ExtractionError(
            code=ErrorCode.UNKNOWN,
            message="Ocurrió un error inesperado al procesar tu consulta. Inténtalo de nuevo.",
        ),
    )


def _unknown_error_trace(extraction: DataExtraction) -> AgentTrace:
    return AgentTrace(
        extraction_id=extraction.extraction_id,
        pipeline="sql",
        query_display="",
        preview_rows=[],
        preview_columns=[],
    )
