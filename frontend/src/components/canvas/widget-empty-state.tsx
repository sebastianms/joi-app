import { Inbox } from "lucide-react";

export function WidgetEmptyState() {
  return (
    <div
      className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center"
      role="status"
      aria-live="polite"
      data-role="widget-empty-state"
    >
      <div
        className="flex h-12 w-12 items-center justify-center rounded-full
          bg-[color:var(--joi-surface-elevated)] border border-[color:var(--joi-border)]"
      >
        <Inbox className="h-5 w-5 text-[color:var(--joi-muted)]" aria-hidden="true" />
      </div>
      <div className="space-y-1.5">
        <p className="text-sm font-medium text-[color:var(--joi-text)]">Sin datos para visualizar</p>
        <p className="max-w-xs text-xs text-[color:var(--joi-muted)] leading-relaxed">
          La consulta se ejecutó correctamente pero no devolvió filas. Ajusta los filtros
          o pregunta por un rango distinto.
        </p>
      </div>
    </div>
  );
}
