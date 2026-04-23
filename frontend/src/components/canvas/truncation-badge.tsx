// FR-013: visible indicator that the widget represents a truncated subset.
// Rendered inside the canvas header (next to the widget title) whenever
// WidgetSpec.truncation_badge is true.

import { AlertTriangle } from "lucide-react";

interface TruncationBadgeProps {
  rowCount: number;
}

export function TruncationBadge({ rowCount }: TruncationBadgeProps) {
  const tooltip = `Se está mostrando un subconjunto (${rowCount.toLocaleString("es")} filas). Reformula tu pregunta para acotar el resultado.`;

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900"
      role="status"
      aria-label={tooltip}
      title={tooltip}
      data-role="truncation-badge"
    >
      <AlertTriangle className="h-3 w-3" aria-hidden="true" />
      Resultado truncado
    </span>
  );
}
