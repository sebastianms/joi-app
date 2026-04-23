// generated from specs/004-widget-generation/contracts/widget-spec-v1.schema.json

export type WidgetType =
  | "table"
  | "bar_chart"
  | "line_chart"
  | "pie_chart"
  | "kpi"
  | "scatter_plot"
  | "heatmap"
  | "area_chart";

export type SelectionSource = "deterministic" | "user_preference" | "fallback";

export type WidgetRenderMode = "ui_framework" | "free_code";

export type UILibrary = "shadcn" | "bootstrap" | "heroui";

export type WidgetErrorCode =
  | "GENERATOR_TIMEOUT"
  | "SPEC_INVALID"
  | "RENDER_TIMEOUT"
  | "RENDER_ERROR"
  | "UNKNOWN";

export interface WidgetBindings {
  x?: string;
  y?: string;
  series?: string;
  value?: string;
  label?: string;
  extra?: Record<string, unknown>;
}

export type FormatHint =
  | "currency"
  | "percent"
  | "integer"
  | "decimal"
  | "datetime"
  | "string";

export interface VisualOptions {
  title?: string;
  subtitle?: string;
  x_label?: string;
  y_label?: string;
  value_format?: string;
  format_hints?: Record<string, FormatHint>;
}

export interface WidgetCode {
  html?: string;
  css?: string;
  js?: string;
}

export interface DataReference {
  extraction_id: string;
  columns: Array<{ name: string; type: string }>;
  row_count: number;
}

export interface WidgetSpec {
  contract_version: "v1";
  widget_id: string;
  extraction_id: string;
  session_id: string;
  render_mode: WidgetRenderMode;
  ui_library?: UILibrary;
  widget_type: WidgetType;
  selection_source: SelectionSource;
  bindings: WidgetBindings;
  visual_options?: VisualOptions;
  code?: WidgetCode;
  data_reference: DataReference;
  truncation_badge: boolean;
  generated_by_model: string;
  generated_at: string;
}

export interface WidgetGenerationTrace {
  trace_id: string;
  extraction_id: string;
  widget_id?: string;
  widget_type_attempted?: WidgetType;
  status: "success" | "fallback" | "error";
  message: string;
  generated_by_model?: string;
  generation_ms: number;
  render_ms?: number;
  error_code?: WidgetErrorCode;
  generated_at: string;
}

// Canvas state — lives in React client only, never persisted
export type CanvasLoadingStage = "idle" | "generating" | "bootstrapping" | "ready" | "error";

export interface CanvasError {
  code: WidgetErrorCode;
  message: string;
}

export interface CanvasState {
  session_id: string;
  current_widget_spec: WidgetSpec | null;
  loading_stage: CanvasLoadingStage;
  last_error: CanvasError | null;
  previous_widget_spec: WidgetSpec | null;
}
