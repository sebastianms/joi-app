// Canvas panel (T138). Orquesta use-canvas y decide qué renderizar según
// el estado: skeleton de generación, skeleton de bootstrap, iframe con el
// widget, empty state o error inline.
//
// El WidgetErrorBanner completo (T403) llega con US4; mientras tanto el
// estado "error" usa un bloque inline mínimo.

"use client";

import { useMemo } from "react";
import { useCanvas } from "@/hooks/use-canvas";
import type { WidgetSpec } from "@/types/widget";
import { WidgetFrame } from "./widget-frame";
import { WidgetLoading } from "./widget-loading";
import { WidgetEmptyState } from "./widget-empty-state";
import { TruncationBadge } from "./truncation-badge";

interface CanvasPanelProps {
  sessionId: string;
  widgetSpec: WidgetSpec | null;
  dataRows: Array<Record<string, unknown>>;
  isGenerating: boolean;
  extractionEmpty: boolean;
}

export function CanvasPanel({
  sessionId,
  widgetSpec,
  dataRows,
  isGenerating,
  extractionEmpty,
}: CanvasPanelProps) {
  const { state, bundleCode, frameHeight, frameRef, handleFrameLoad } = useCanvas({
    sessionId,
    widgetSpec,
    dataRows,
  });

  const title = useMemo(() => {
    if (!widgetSpec) return "Canvas de widgets";
    const t = widgetSpec.visual_options?.title;
    return t ? `Widget: ${t}` : `Widget ${widgetSpec.widget_type}`;
  }, [widgetSpec]);

  if (isGenerating) {
    return (
      <PanelShell>
        <WidgetLoading stage="generating" />
      </PanelShell>
    );
  }

  if (extractionEmpty && !widgetSpec) {
    return (
      <PanelShell>
        <WidgetEmptyState />
      </PanelShell>
    );
  }

  if (!widgetSpec) {
    return (
      <PanelShell dashed>
        <div className="flex h-full items-center justify-center p-6 text-center text-sm text-muted-foreground">
          <p className="max-w-sm">
            Los widgets generados aparecerán aquí cuando solicites visualizar tus datos.
          </p>
        </div>
      </PanelShell>
    );
  }

  if (state.loading_stage === "error" && state.last_error) {
    return (
      <PanelShell>
        <div
          className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center"
          role="alert"
          data-role="widget-error"
        >
          <p className="text-sm font-medium text-destructive">
            No se pudo renderizar el widget
          </p>
          <p className="max-w-xs text-xs text-muted-foreground">{state.last_error.message}</p>
        </div>
      </PanelShell>
    );
  }

  if (!bundleCode || state.loading_stage === "idle") {
    return (
      <PanelShell>
        <WidgetLoading stage="bootstrapping" />
      </PanelShell>
    );
  }

  return (
    <PanelShell>
      <div className="flex flex-col gap-2 p-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-foreground">
            {widgetSpec.visual_options?.title ?? "Widget"}
          </h2>
          {widgetSpec.truncation_badge && (
            <TruncationBadge rowCount={widgetSpec.data_reference.row_count} />
          )}
        </div>
        <div
          className="relative w-full overflow-hidden rounded-lg border border-border bg-background"
          style={{ height: frameHeight }}
          data-role="widget-container"
        >
          <WidgetFrame
            ref={frameRef}
            bundleCode={bundleCode}
            title={title}
            onLoad={handleFrameLoad}
          />
          {state.loading_stage === "bootstrapping" && (
            <div className="pointer-events-none absolute inset-0 rounded-lg bg-card">
              <WidgetLoading stage="bootstrapping" />
            </div>
          )}
        </div>
      </div>
    </PanelShell>
  );
}

function PanelShell({
  children,
  dashed = false,
}: {
  children: React.ReactNode;
  dashed?: boolean;
}) {
  return (
    <section
      className={
        dashed
          ? "flex min-h-0 flex-1 flex-col rounded-xl border border-dashed border-border bg-card"
          : "flex min-h-0 flex-1 flex-col rounded-xl border border-border bg-card"
      }
      aria-label="Canvas de widgets"
      data-role="canvas-panel"
    >
      {children}
    </section>
  );
}
