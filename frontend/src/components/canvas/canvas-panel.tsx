"use client";

import { useMemo, useState } from "react";
import { useCanvas } from "@/hooks/use-canvas";
import { useCollections } from "@/hooks/use-collections";
import type { WidgetSpec } from "@/types/widget";
import { Button } from "@/components/ui/button";
import { SaveWidgetDialog } from "@/components/collections/SaveWidgetDialog";
import { WidgetFrame } from "./widget-frame";
import { WidgetLoading } from "./widget-loading";
import { WidgetEmptyState } from "./widget-empty-state";
import { TruncationBadge } from "./truncation-badge";
import { WidgetErrorBanner } from "./widget-error-banner";

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
  const { collections, fetchCollections, createCollection, saveWidget } = useCollections();
  const [dialogOpen, setDialogOpen] = useState(false);

  async function handleOpenSaveDialog() {
    await fetchCollections(sessionId);
    setDialogOpen(true);
  }

  async function handleSave(displayName: string, collectionIds: string[]) {
    if (!widgetSpec) return;
    await saveWidget(widgetSpec.widget_id, {
      session_id: sessionId,
      display_name: displayName,
      collection_ids: collectionIds,
    });
  }

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
      <PanelShell>
        <IdleState />
      </PanelShell>
    );
  }

  if (state.loading_stage === "error" && state.last_error) {
    const hasPrevious = state.previous_widget_spec !== null && bundleCode;
    if (hasPrevious) {
      return (
        <PanelShell>
          <div className="flex flex-col gap-2 p-3">
            <WidgetErrorBanner error={state.last_error} />
            <div
              className="relative w-full overflow-hidden rounded-lg border border-[color:var(--joi-border)] bg-[color:var(--joi-surface)]"
              style={{ height: frameHeight }}
              data-role="widget-container"
            >
              <WidgetFrame
                ref={frameRef}
                bundleCode={bundleCode}
                title={title}
                onLoad={handleFrameLoad}
              />
            </div>
          </div>
        </PanelShell>
      );
    }
    return (
      <PanelShell>
        <div className="flex h-full flex-col items-center justify-center">
          <WidgetErrorBanner error={state.last_error} />
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
    <>
      <PanelShell>
        <div className="flex flex-col gap-2 p-3 h-full">
          <div className="flex items-center justify-between flex-shrink-0">
            <h2 className="text-sm font-medium text-[color:var(--joi-text)] tracking-tight">
              {widgetSpec.visual_options?.title ?? "Widget"}
            </h2>
            <div className="flex items-center gap-2">
              {widgetSpec.truncation_badge && (
                <TruncationBadge rowCount={widgetSpec.data_reference.row_count} />
              )}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleOpenSaveDialog}
                data-role="widget-save-button"
                className="border-[color:var(--joi-border)] text-[color:var(--joi-muted)]
                  hover:border-[color:var(--joi-accent)] hover:text-[color:var(--joi-accent)]
                  transition-colors"
              >
                Guardar
              </Button>
            </div>
          </div>
          <div
            className="relative w-full overflow-hidden rounded-lg border border-[color:var(--joi-border)] bg-[color:var(--joi-surface)]"
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
              <WidgetLoading stage="bootstrapping" />
            )}
          </div>
        </div>
      </PanelShell>
      <SaveWidgetDialog
        open={dialogOpen}
        collections={collections}
        onClose={() => setDialogOpen(false)}
        onSave={handleSave}
        onCreateCollection={(name) => createCollection(sessionId, name)}
      />
    </>
  );
}

function IdleState() {
  const dots = Array.from({ length: 48 });
  return (
    <div
      className="flex h-full flex-col items-center justify-center gap-6 p-10 text-center"
      data-role="canvas-idle"
    >
      <div
        className="grid gap-2.5 opacity-[0.08]"
        style={{ gridTemplateColumns: "repeat(12, 1fr)" }}
        aria-hidden="true"
      >
        {dots.map((_, i) => (
          <span key={i} className="block w-1 h-1 rounded-full bg-[color:var(--joi-text)]" />
        ))}
      </div>
      <div>
        <h2 className="text-base font-semibold tracking-wide text-[color:var(--joi-text)] mb-2">
          Tu canvas está esperando
        </h2>
        <p className="text-sm text-[color:var(--joi-muted)] max-w-xs leading-relaxed">
          Pregunta algo sobre tus datos y Joi generará una visualización aquí.
        </p>
      </div>
    </div>
  );
}

function PanelShell({ children }: { children: React.ReactNode }) {
  return (
    <section
      className="flex min-h-0 flex-1 flex-col
        bg-[color:var(--joi-surface)]/40 backdrop-blur-sm"
      aria-label="Canvas de widgets"
      data-role="canvas-panel"
    >
      {children}
    </section>
  );
}
