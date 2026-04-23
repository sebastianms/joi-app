// Canvas skeleton shown while the architect generates the spec (generating)
// and while the iframe bootstraps the runtime (bootstrapping). Purely presentational.

import type { CanvasLoadingStage } from "@/types/widget";

interface WidgetLoadingProps {
  stage: Extract<CanvasLoadingStage, "generating" | "bootstrapping">;
}

const STAGE_COPY: Record<WidgetLoadingProps["stage"], { title: string; detail: string }> = {
  generating: {
    title: "Construyendo el widget…",
    detail: "El arquitecto está eligiendo el tipo de visualización según tus datos.",
  },
  bootstrapping: {
    title: "Renderizando el widget…",
    detail: "Cargando el runtime dentro del canvas aislado.",
  },
};

export function WidgetLoading({ stage }: WidgetLoadingProps) {
  const copy = STAGE_COPY[stage];

  return (
    <div
      className="flex h-full flex-col gap-4 p-6"
      role="status"
      aria-live="polite"
      aria-label={copy.title}
      data-role="widget-loading"
      data-stage={stage}
    >
      <div className="space-y-2">
        <p className="text-sm font-medium text-foreground">{copy.title}</p>
        <p className="text-xs text-muted-foreground">{copy.detail}</p>
      </div>
      <div className="flex flex-1 flex-col gap-3 rounded-lg border border-border bg-card p-4">
        <div className="h-4 w-1/3 animate-pulse rounded bg-muted" />
        <div className="h-3 w-1/2 animate-pulse rounded bg-muted" />
        <div className="mt-2 flex-1 animate-pulse rounded bg-muted" />
      </div>
    </div>
  );
}
