import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.models.render_mode import UILibrary


class WidgetType(str, Enum):
    TABLE = "table"
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    KPI = "kpi"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"
    AREA_CHART = "area_chart"


class SelectionSource(str, Enum):
    DETERMINISTIC = "deterministic"
    USER_PREFERENCE = "user_preference"
    FALLBACK = "fallback"


class WidgetRenderMode(str, Enum):
    UI_FRAMEWORK = "ui_framework"
    FREE_CODE = "free_code"


class WidgetErrorCode(str, Enum):
    GENERATOR_TIMEOUT = "GENERATOR_TIMEOUT"
    SPEC_INVALID = "SPEC_INVALID"
    RENDER_TIMEOUT = "RENDER_TIMEOUT"
    RENDER_ERROR = "RENDER_ERROR"
    UNKNOWN = "UNKNOWN"


class WidgetBindings(BaseModel):
    """Column → visual role mapping. Keys depend on widget_type."""

    x: Optional[str] = None
    y: Optional[str] = None
    series: Optional[str] = None
    value: Optional[str] = None
    label: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class VisualOptions(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    value_format: Optional[str] = None


class WidgetCode(BaseModel):
    html: Optional[str] = None
    css: Optional[str] = None
    js: Optional[str] = None


class DataReference(BaseModel):
    """Per widget-spec-v1 schema: rows are NOT embedded; they travel via
    postMessage from the Canvas host into the iframe. The spec only carries
    shape metadata so the chat transcript stays compact."""

    extraction_id: str
    columns: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = Field(ge=0, default=0)


class WidgetSpec(BaseModel):
    contract_version: Literal["v1"] = "v1"
    widget_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    extraction_id: str
    session_id: str
    render_mode: WidgetRenderMode
    ui_library: Optional[UILibrary] = None
    widget_type: WidgetType
    selection_source: SelectionSource
    bindings: WidgetBindings = Field(default_factory=WidgetBindings)
    visual_options: Optional[VisualOptions] = None
    code: Optional[WidgetCode] = None
    data_reference: DataReference
    truncation_badge: bool = False
    generated_by_model: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WidgetGenerationTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    extraction_id: str
    widget_id: Optional[str] = None
    widget_type_attempted: Optional[WidgetType] = None
    status: Literal["success", "fallback", "error"]
    message: str
    generated_by_model: Optional[str] = None
    generation_ms: int
    render_ms: Optional[int] = None
    error_code: Optional[WidgetErrorCode] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
