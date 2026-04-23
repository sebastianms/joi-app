// Canvas empty state when the extraction succeeded but returned 0 rows.
// FR-015 prevents widget generation in that case, so the canvas shows this
// informative block instead of an empty skeleton or a broken chart.

import { Inbox } from "lucide-react";

export function WidgetEmptyState() {
  return (
    <div
      className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center"
      role="status"
      aria-live="polite"
      data-role="widget-empty-state"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
        <Inbox className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">Sin datos para visualizar</p>
        <p className="max-w-xs text-xs text-muted-foreground">
          La consulta se ejecutó correctamente pero no devolvió filas. Ajusta los filtros
          o pregunta por un rango distinto para generar un widget.
        </p>
      </div>
    </div>
  );
}
