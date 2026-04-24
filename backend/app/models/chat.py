from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntentType(str, Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"


class Message(BaseModel):
    role: Role
    content: str
    extraction: Optional["DataExtraction"] = None
    trace: Optional["AgentTrace"] = None


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class WidgetSummary(BaseModel):
    id: str
    display_name: str


class TriageResult(BaseModel):
    intent_type: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    matched_pattern: Optional[str] = None
    suggested_route: str
    preferred_widget_type: Optional["WidgetType"] = None
    recovered_widget_name: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    intent_type: IntentType
    extraction: Optional["DataExtraction"] = None
    trace: Optional["AgentTrace"] = None
    widget_spec: Optional["WidgetSpec"] = None
    render_mode_profile: Optional["RenderModeProfileRef"] = None
    recovered_widget: Optional[WidgetSummary] = None
    candidates: Optional[list[WidgetSummary]] = None

    model_config = {"populate_by_name": True}


# Importación diferida para evitar ciclos; rebuild resuelve las forward references
from app.models.extraction import AgentTrace, DataExtraction  # noqa: E402
from app.models.widget import WidgetSpec, WidgetType  # noqa: E402
from app.models.render_mode import RenderModeProfileRef  # noqa: E402

Message.model_rebuild()
TriageResult.model_rebuild()
ChatResponse.model_rebuild()
