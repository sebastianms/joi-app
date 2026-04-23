import pytest

from app.models.chat import ChatRequest, IntentType, Message, Role
from app.models.connection import DataSourceType
from app.models.extraction import (
    AgentTrace,
    ColumnDescriptor,
    DataExtraction,
    ErrorCode,
    ExtractionError,
    QueryPlan,
    SourceType,
)
from app.models.widget import SelectionSource, WidgetType
from app.services.chat_manager import ChatManagerService
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService
from app.services.widget.architect_service import (
    ArchitectOutcome,
    ArchitectRequest,
)
from app.services.widget.fallback_builder import build_table_fallback


class StubLLM(LLMGateway):
    """Test double: always returns a fixed response."""

    def complete(self, history: list[Message]) -> str:
        return "stub_response"


class StubDataAgent:
    def __init__(
        self, extraction: DataExtraction | None = None, trace: AgentTrace | None = None
    ) -> None:
        self.extraction = extraction or _success_extraction()
        self.trace = trace or _trace_for(self.extraction)
        self.calls: list[tuple[str, str]] = []

    async def extract(
        self, session_id: str, prompt: str
    ) -> tuple[DataExtraction, AgentTrace]:
        self.calls.append((session_id, prompt))
        return self.extraction, self.trace


def _success_extraction(row_count: int = 5, truncated: bool = False) -> DataExtraction:
    return DataExtraction(
        session_id="s1",
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression="SELECT 1"),
        columns=[ColumnDescriptor(name="x", type="integer")],
        rows=[{"x": i} for i in range(row_count)],
        row_count=row_count,
        truncated=truncated,
        status="success",
    )


def _error_extraction(code: ErrorCode, message: str) -> DataExtraction:
    return DataExtraction(
        session_id="s1",
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression=""),
        row_count=0,
        status="error",
        error=ExtractionError(code=code, message=message),
    )


def _trace_for(extraction: DataExtraction) -> AgentTrace:
    return AgentTrace(
        extraction_id=extraction.extraction_id,
        pipeline="sql",
        query_display=extraction.query_plan.expression,
        preview_rows=extraction.rows[:10],
        preview_columns=extraction.columns,
    )


class RecordingArchitect:
    """Returns a deterministic table spec and records every invocation."""

    def __init__(self) -> None:
        self.calls: list[ArchitectRequest] = []

    async def __call__(self, request: ArchitectRequest) -> ArchitectOutcome:
        self.calls.append(request)
        spec = build_table_fallback(request.extraction)
        return ArchitectOutcome(spec=spec, trace=None)


@pytest.fixture
def architect() -> RecordingArchitect:
    return RecordingArchitect()


@pytest.fixture
def manager(architect: RecordingArchitect) -> ChatManagerService:
    return ChatManagerService(
        triage=TriageEngineService(), llm=StubLLM(), architect=architect
    )


# --- Routing ---

@pytest.mark.asyncio
async def test_simple_intent_calls_llm(manager: ChatManagerService):
    agent = StubDataAgent()
    response = await manager.handle(
        ChatRequest(session_id="s1", message="hola"), agent
    )
    assert response.intent_type == IntentType.SIMPLE
    assert response.response == "stub_response"
    assert response.extraction is None
    assert response.trace is None
    assert agent.calls == []


@pytest.mark.asyncio
async def test_complex_intent_invokes_data_agent(manager: ChatManagerService):
    agent = StubDataAgent(_success_extraction(row_count=7))
    response = await manager.handle(
        ChatRequest(session_id="s1", message="muéstrame las ventas por mes"), agent
    )

    assert response.intent_type == IntentType.COMPLEX
    assert response.extraction is not None
    assert response.trace is not None
    assert response.response == "Encontré 7 filas."
    assert agent.calls == [("s1", "muéstrame las ventas por mes")]


@pytest.mark.asyncio
async def test_complex_intent_truncated_mentions_limit(manager: ChatManagerService):
    agent = StubDataAgent(_success_extraction(row_count=500, truncated=True))
    response = await manager.handle(
        ChatRequest(session_id="s1", message="dame todas las filas"), agent
    )
    assert "truncado" in response.response


@pytest.mark.asyncio
async def test_complex_intent_empty_result_specific_message(manager: ChatManagerService):
    agent = StubDataAgent(_success_extraction(row_count=0))
    response = await manager.handle(
        ChatRequest(session_id="s1", message="dame las ventas del año pasado"), agent
    )
    assert response.response == "La consulta no devolvió filas."
    assert response.extraction.row_count == 0
    assert response.extraction.status == "success"


@pytest.mark.asyncio
async def test_complex_intent_error_uses_error_message(manager: ChatManagerService):
    extraction = _error_extraction(
        ErrorCode.NO_CONNECTION, "No hay una fuente de datos activa."
    )
    agent = StubDataAgent(extraction=extraction, trace=_trace_for(extraction))
    response = await manager.handle(
        ChatRequest(session_id="s1", message="dame las ventas"), agent
    )
    assert "No hay una fuente de datos activa" in response.response
    assert response.extraction.status == "error"


# --- Session history ---

@pytest.mark.asyncio
async def test_history_accumulates_messages(manager: ChatManagerService):
    agent = StubDataAgent()
    await manager.handle(ChatRequest(session_id="s2", message="hola"), agent)
    await manager.handle(ChatRequest(session_id="s2", message="gracias"), agent)
    history = manager.get_history("s2")
    assert len(history) == 4  # 2 user + 2 assistant


@pytest.mark.asyncio
async def test_history_isolated_between_sessions(manager: ChatManagerService):
    agent = StubDataAgent()
    await manager.handle(ChatRequest(session_id="session-a", message="hola"), agent)
    await manager.handle(ChatRequest(session_id="session-b", message="hola"), agent)
    assert len(manager.get_history("session-a")) == 2
    assert len(manager.get_history("session-b")) == 2


@pytest.mark.asyncio
async def test_history_roles_are_correct(manager: ChatManagerService):
    agent = StubDataAgent()
    await manager.handle(ChatRequest(session_id="s3", message="hola"), agent)
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


@pytest.mark.asyncio
async def test_llm_receives_full_history_as_context():
    llm = HistoryCaptureLLM()
    manager = ChatManagerService(
        triage=TriageEngineService(), llm=llm, architect=RecordingArchitect()
    )
    agent = StubDataAgent()
    await manager.handle(ChatRequest(session_id="ctx", message="hola"), agent)
    await manager.handle(ChatRequest(session_id="ctx", message="gracias"), agent)
    assert len(llm.received) == 3
    assert llm.received[-1].content == "gracias"


@pytest.mark.asyncio
async def test_assistant_message_carries_extraction_and_trace(manager: ChatManagerService):
    agent = StubDataAgent()
    await manager.handle(
        ChatRequest(session_id="trace-1", message="dame las ventas"), agent
    )
    history = manager.get_history("trace-1")
    assistant_msg = history[1]
    assert assistant_msg.role == Role.ASSISTANT
    assert assistant_msg.extraction is not None
    assert assistant_msg.trace is not None


# --- Widget integration (T107, FR-015) ---


@pytest.mark.asyncio
async def test_widget_generated_on_successful_extraction_with_rows(
    manager: ChatManagerService, architect: RecordingArchitect
):
    agent = StubDataAgent(_success_extraction(row_count=3))
    response = await manager.handle(
        ChatRequest(session_id="w1", message="ventas por región"), agent
    )

    assert response.widget_spec is not None
    assert response.widget_spec.widget_type == WidgetType.TABLE
    assert len(architect.calls) == 1


@pytest.mark.asyncio
async def test_widget_not_generated_on_extraction_error(
    manager: ChatManagerService, architect: RecordingArchitect
):
    """FR-015: error extractions must not trigger the architect."""
    extraction = _error_extraction(ErrorCode.SECURITY_REJECTION, "bloqueado")
    agent = StubDataAgent(extraction=extraction, trace=_trace_for(extraction))

    response = await manager.handle(
        ChatRequest(session_id="w2", message="drop table"), agent
    )

    assert response.widget_spec is None
    assert architect.calls == []


@pytest.mark.asyncio
async def test_widget_not_generated_on_empty_result(
    manager: ChatManagerService, architect: RecordingArchitect
):
    agent = StubDataAgent(_success_extraction(row_count=0))
    response = await manager.handle(
        ChatRequest(session_id="w3", message="ventas del año 1800"), agent
    )

    assert response.widget_spec is None
    assert architect.calls == []


@pytest.mark.asyncio
async def test_widget_not_generated_on_simple_intent(
    manager: ChatManagerService, architect: RecordingArchitect
):
    agent = StubDataAgent()
    await manager.handle(ChatRequest(session_id="w4", message="hola"), agent)

    assert architect.calls == []


@pytest.mark.asyncio
async def test_architect_receives_user_intent(
    manager: ChatManagerService, architect: RecordingArchitect
):
    agent = StubDataAgent(_success_extraction(row_count=2))
    await manager.handle(
        ChatRequest(session_id="w5", message="dame el top 5 de ventas"), agent
    )

    assert architect.calls[0].user_intent == "dame el top 5 de ventas"


@pytest.mark.asyncio
async def test_architect_failure_does_not_break_the_response():
    """Architect exceptions must not bubble to the caller (FR-009)."""

    async def failing_architect(request: ArchitectRequest) -> ArchitectOutcome:
        raise RuntimeError("architect crashed")

    manager = ChatManagerService(
        triage=TriageEngineService(), llm=StubLLM(), architect=failing_architect
    )
    agent = StubDataAgent(_success_extraction(row_count=3))
    response = await manager.handle(
        ChatRequest(session_id="w6", message="ventas"), agent
    )

    assert response.extraction is not None
    assert response.widget_spec is None


@pytest.mark.asyncio
async def test_widget_trace_attached_to_agent_trace():
    from app.models.widget import WidgetGenerationTrace

    async def fake_architect(request: ArchitectRequest) -> ArchitectOutcome:
        spec = build_table_fallback(request.extraction)
        trace = WidgetGenerationTrace(
            extraction_id=spec.extraction_id,
            widget_id=spec.widget_id,
            widget_type_attempted=WidgetType.TABLE,
            status="success",
            message="ok",
            generated_by_model="deterministic",
            generation_ms=0,
        )
        return ArchitectOutcome(spec=spec, trace=trace)

    manager = ChatManagerService(
        triage=TriageEngineService(), llm=StubLLM(), architect=fake_architect
    )
    agent = StubDataAgent(_success_extraction(row_count=3))
    response = await manager.handle(
        ChatRequest(session_id="w7", message="ventas"), agent
    )

    assert response.trace.widget_generation is not None
    assert response.trace.widget_generation.status == "success"


# --- US2: Widget preference over prior extraction (T204, T205, T206, T207) ---


def _success_extraction_with_num(
    row_count: int = 5, session_id: str = "s1"
) -> DataExtraction:
    """Extraction with a categorical + numeric column for compatibility tests."""
    return DataExtraction(
        session_id=session_id,
        connection_id="conn-1",
        source_type=SourceType.SQL_SQLITE,
        query_plan=QueryPlan(language="sql", expression="SELECT 1"),
        columns=[
            ColumnDescriptor(name="cat", type="string"),
            ColumnDescriptor(name="val", type="integer"),
        ],
        rows=[{"cat": f"c{i}", "val": i} for i in range(row_count)],
        row_count=row_count,
        status="success",
    )


@pytest.mark.asyncio
async def test_widget_preference_reuses_same_extraction_id(
    manager: ChatManagerService, architect: RecordingArchitect
):
    """T206: preference request must pass the cached extraction (same extraction_id)."""
    extraction = _success_extraction_with_num(row_count=5, session_id="pref-1")
    agent = StubDataAgent(extraction=extraction, trace=_trace_for(extraction))

    # First turn: data extraction
    await manager.handle(
        ChatRequest(session_id="pref-1", message="muéstrame las ventas"), agent
    )
    first_extraction_id = extraction.extraction_id

    # Second turn: preference request — "scatter" has no complex keyword so goes via widget_preference route
    pref_response = await manager.handle(
        ChatRequest(session_id="pref-1", message="prefiero scatter"), agent
    )

    assert len(architect.calls) == 2
    # Second call must use the cached extraction, not a new one
    assert architect.calls[1].extraction.extraction_id == first_extraction_id
    # Data agent should NOT have been called a second time
    assert len(agent.calls) == 1


@pytest.mark.asyncio
async def test_widget_preference_sets_preferred_type(
    manager: ChatManagerService, architect: RecordingArchitect
):
    """T204: architect receives the user-expressed widget type."""
    extraction = _success_extraction_with_num(row_count=5, session_id="pref-2")
    agent = StubDataAgent(extraction=extraction, trace=_trace_for(extraction))

    await manager.handle(
        ChatRequest(session_id="pref-2", message="muéstrame las ventas"), agent
    )
    await manager.handle(
        ChatRequest(session_id="pref-2", message="prefiero scatter"), agent
    )

    assert architect.calls[1].preferred_widget_type == WidgetType.SCATTER_PLOT


@pytest.mark.asyncio
async def test_widget_preference_without_prior_extraction_falls_back_to_llm(
    manager: ChatManagerService, architect: RecordingArchitect
):
    """No prior extraction → preference phrase treated as SIMPLE, LLM responds."""
    agent = StubDataAgent()
    response = await manager.handle(
        ChatRequest(session_id="pref-3", message="prefiero scatter"), agent
    )

    assert response.intent_type == IntentType.SIMPLE
    assert response.response == "stub_response"
    assert architect.calls == []


@pytest.mark.asyncio
async def test_incompatible_preference_returns_explanation_and_keeps_session(
    architect: RecordingArchitect,
):
    """T207: incompatible preference → explanation in chat, no new widget, session stays."""
    from app.services.widget.architect_service import PreferenceHint

    async def incompatible_architect(request: ArchitectRequest) -> ArchitectOutcome:
        if request.preferred_widget_type is not None:
            hint = PreferenceHint(
                requested=request.preferred_widget_type,
                reason="datos insuficientes",
                alternatives=[WidgetType.TABLE, WidgetType.BAR_CHART],
            )
            return ArchitectOutcome(spec=None, trace=None, preference_hint=hint)
        spec = build_table_fallback(request.extraction)
        return ArchitectOutcome(spec=spec, trace=None)

    manager = ChatManagerService(
        triage=TriageEngineService(), llm=StubLLM(), architect=incompatible_architect
    )
    extraction = _success_extraction_with_num(row_count=5, session_id="pref-4")
    agent = StubDataAgent(extraction=extraction, trace=_trace_for(extraction))

    # First turn: successful extraction
    first_response = await manager.handle(
        ChatRequest(session_id="pref-4", message="muéstrame las ventas"), agent
    )
    assert first_response.widget_spec is not None

    # Second turn: incompatible preference
    pref_response = await manager.handle(
        ChatRequest(session_id="pref-4", message="prefiero scatter"), agent
    )

    assert pref_response.widget_spec is None
    assert "scatter_plot" in pref_response.response or "scatter" in pref_response.response.lower()
    assert "datos insuficientes" in pref_response.response
    # Session still operational: can send another message
    follow_up = await manager.handle(
        ChatRequest(session_id="pref-4", message="hola"), agent
    )
    assert follow_up.response == "stub_response"
