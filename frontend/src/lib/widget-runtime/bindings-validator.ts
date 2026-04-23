// Runtime-side bindings validator (T408, mirror of backend's bindings_validator.py).
//
// Runs inside the iframe BEFORE dispatching the renderer. If the spec is
// semantically invalid (missing bindings required by its widget_type), the
// runtime emits widget:error to the host instead of rendering broken UI.

import type { WidgetSpec, WidgetType } from "@/types/widget";

const REQUIRED_BINDINGS: Record<WidgetType, ReadonlyArray<keyof WidgetSpec["bindings"]>> = {
  table: [],
  bar_chart: ["x", "y"],
  line_chart: ["x", "y"],
  area_chart: ["x", "y"],
  scatter_plot: ["x", "y"],
  heatmap: ["x", "y", "value"],
  pie_chart: ["label", "value"],
  kpi: ["value"],
};

export function findMissingBindings(spec: WidgetSpec): string[] {
  const required = REQUIRED_BINDINGS[spec.widget_type] ?? [];
  return required.filter((key) => {
    const value = spec.bindings[key];
    return value === undefined || value === null || value === "";
  });
}
