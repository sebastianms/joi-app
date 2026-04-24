from collections import defaultdict
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from app.models.chat import ChatRequest, ChatResponse, IntentType, Message, Role
from app.models.extraction import AgentTrace, DataExtraction, ErrorCode, ExtractionError, QueryPlan, SourceType
from app.models.widget import WidgetSpec, WidgetType
from app.services.data_agent_service import DataAgentService
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService
from app.services.widget_recovery_service import WidgetRecoveryService
from app.services.widget.architect_service import (
    ArchitectOutcome,
    ArchitectRequest,
    PreferenceHint,
    build_widget,
)

_logger = logging.getLogger(__name__)

SessionHistory = dict[str, list[Message]]
LastExtractionCache = dict[str, DataExtraction]

ArchitectFn = Callable[[ArchitectRequest], Awaitable[ArchitectOutcome]]


@dataclass(frozen=True)
class ExtractionTurn:
    """Intermediate state carried from extraction → widget generation."""

    extraction: DataExtraction
    trace: AgentTrace


class ChatManagerService:
    """Orchestrates triage classification, LLM responses and data agent extraction per session."""

    def __init__(
        self,
        triage: TriageEngineService,
        llm: LLMGateway,
        architect: ArchitectFn = build_widget,
    ) -> None:
        self._triage = triage
        self._llm = llm
        self._architect = architect
        self._history: SessionHistory = defaultdict(list)
        # Stores the last successful extraction per session for US2 widget preference.
        self._last_extraction: LastExtractionCache = {}

    async def handle(
        self, request: ChatRequest, data_agent: DataAgentService, widget_recovery: WidgetRecoveryService
    ) -> ChatResponse:
        user_message = Message(role=Role.USER, content=request.message)
        session = self._history[request.session_id]
        session.append(user_message)

        has_prior = request.session_id in self._last_extraction
        triage_result = self._triage.classify(request.message, has_prior_extraction=has_prior)

        if triage_result.suggested_route == "widget_recovery" and triage_result.recovered_widget_name:
            return await self._handle_recovery(request, triage_result.recovered_widget_name, widget_recovery)

        # US2: when the user expresses a widget-type preference AND we have a prior
        # extraction, regenerate the widget from cache without re-querying the data
        # source. This covers both the pure preference path (suggested_route =
        # widget_preference) and the mixed path where a complex keyword co-occurs
        # with a preference phrase (e.g. "muéstralo como tabla").
        if has_prior and triage_result.preferred_widget_type is not None:
            return await self._respond_with_widget_preference(
                request, session, triage_result.preferred_widget_type
            )

        if triage_result.intent_type == IntentType.COMPLEX:
            turn = await self._run_extraction(request, data_agent)
            return await self._respond_with_extraction(request, session, turn, triage_result.intent_type)

        response_text = self._llm.complete(list(session))
        assistant_message = Message(role=Role.ASSISTANT, content=response_text)
        session.append(assistant_message)
        return ChatResponse(
            response=response_text,
            intent_type=triage_result.intent_type,
        )

    async def _handle_recovery(
        self, request: ChatRequest, name_query: str, widget_recovery: WidgetRecoveryService
    ) -> ChatResponse:
        session = self._history[request.session_id]
        match, candidates = await widget_recovery.find(request.session_id, name_query)
        if match:
            response_text = f"Encontré el widget \"{match.display_name}\"."
            session.append(Message(role=Role.ASSISTANT, content=response_text))
            return ChatResponse(
                response=response_text,
                intent_type=IntentType.SIMPLE,
                recovered_widget=match,
            )
        if candidates:
            names = ", ".join(f'"{c.display_name}"' for c in candidates)
            response_text = f"Encontré varios widgets que podrían coincidir: {names}. ¿Cuál quieres abrir?"
            session.append(Message(role=Role.ASSISTANT, content=response_text))
            return ChatResponse(
                response=response_text,
                intent_type=IntentType.SIMPLE,
                candidates=candidates,
            )
        response_text = f"No encontré ningún widget guardado con el nombre \"{name_query}\"."
        session.append(Message(role=Role.ASSISTANT, content=response_text))
        return ChatResponse(response=response_text, intent_type=IntentType.SIMPLE)

    async def _run_extraction(
        self, request: ChatRequest, data_agent: DataAgentService
    ) -> ExtractionTurn:
        try:
            extraction, trace = await data_agent.extract(request.session_id, request.message)
        except Exception as exc:
            _logger.exception("Unexpected error in data_agent.extract: %s", exc)
            extraction = _unknown_error_extraction(request.session_id)
            trace = _unknown_error_trace(extraction)
        return ExtractionTurn(extraction=extraction, trace=trace)

    async def _respond_with_extraction(
        self,
        request: ChatRequest,
        session: list[Message],
        turn: ExtractionTurn,
        intent_type: IntentType,
    ) -> ChatResponse:
        widget_spec = await self._maybe_build_widget(request, turn)
        if _widget_eligible(turn.extraction):
            self._last_extraction[request.session_id] = turn.extraction
        response_text = _format_extraction_response(turn.extraction)
        assistant_message = Message(
            role=Role.ASSISTANT,
            content=response_text,
            extraction=turn.extraction,
            trace=turn.trace,
        )
        session.append(assistant_message)
        return ChatResponse(
            response=response_text,
            intent_type=intent_type,
            extraction=turn.extraction,
            trace=turn.trace,
            widget_spec=widget_spec,
        )

    async def _respond_with_widget_preference(
        self,
        request: ChatRequest,
        session: list[Message],
        preferred_widget_type: WidgetType,
    ) -> ChatResponse:
        """US2: regenerate widget from the cached extraction without re-querying the data source."""
        prior_extraction = self._last_extraction[request.session_id]
        stub_trace = _stub_trace_for_preference(prior_extraction)

        try:
            outcome = await self._architect(
                ArchitectRequest(
                    extraction=prior_extraction,
                    user_intent=request.message,
                    preferred_widget_type=preferred_widget_type,
                )
            )
        except Exception as exc:
            _logger.exception("Unexpected error in architect (preference path): %s", exc)
            response_text = "No pude actualizar la visualización. Inténtalo de nuevo."
            session.append(Message(role=Role.ASSISTANT, content=response_text))
            return ChatResponse(response=response_text, intent_type=IntentType.COMPLEX)

        if outcome.preference_hint is not None:
            response_text = _format_incompatibility_message(outcome.preference_hint)
            session.append(Message(role=Role.ASSISTANT, content=response_text))
            return ChatResponse(response=response_text, intent_type=IntentType.COMPLEX)

        if outcome.trace is not None:
            stub_trace.widget_generation = outcome.trace

        response_text = f"Widget actualizado como {preferred_widget_type.value}."
        assistant_message = Message(
            role=Role.ASSISTANT,
            content=response_text,
            extraction=prior_extraction,
            trace=stub_trace,
        )
        session.append(assistant_message)
        return ChatResponse(
            response=response_text,
            intent_type=IntentType.COMPLEX,
            extraction=prior_extraction,
            trace=stub_trace,
            widget_spec=outcome.spec,
        )

    async def _maybe_build_widget(
        self, request: ChatRequest, turn: ExtractionTurn
    ) -> Optional[WidgetSpec]:
        if not _widget_eligible(turn.extraction):
            return None
        try:
            outcome = await self._architect(
                ArchitectRequest(
                    extraction=turn.extraction,
                    user_intent=request.message,
                )
            )
        except Exception as exc:
            _logger.exception("Unexpected error in architect: %s", exc)
            return None
        if outcome.trace is not None:
            turn.trace.widget_generation = outcome.trace
        return outcome.spec

    def get_history(self, session_id: str) -> list[Message]:
        return list(self._history[session_id])


def _widget_eligible(extraction: DataExtraction) -> bool:
    """FR-015: widget generation requires a successful extraction with data."""
    return extraction.status == "success" and extraction.row_count > 0


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


def _stub_trace_for_preference(extraction: DataExtraction) -> AgentTrace:
    """Minimal trace carrier for the widget-preference path (reuses prior extraction, no new query)."""
    return AgentTrace(
        extraction_id=extraction.extraction_id,
        pipeline="sql",
        query_display="",
        preview_rows=[],
        preview_columns=[],
    )


def _format_incompatibility_message(hint: PreferenceHint) -> str:
    alternatives = ", ".join(t.value for t in hint.alternatives) if hint.alternatives else "tabla"
    return (
        f"El tipo '{hint.requested.value}' no es compatible con los datos actuales: {hint.reason}. "
        f"Alternativas válidas: {alternatives}."
    )
