"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import type { Collection, WidgetInCollection } from "@/hooks/use-collections";

interface CollectionManagerProps {
  collectionId: string | null;
  sessionId: string;
  collections: Collection[];
  onFetchWidgets: (collectionId: string, sessionId: string) => Promise<WidgetInCollection[]>;
  onRemoveWidget: (collectionId: string, widgetId: string, sessionId: string) => Promise<boolean>;
  onMoveWidget: (
    fromCollectionId: string,
    toCollectionId: string,
    widgetId: string,
    sessionId: string,
  ) => Promise<boolean>;
}

export function CollectionManager({
  collectionId,
  sessionId,
  collections,
  onFetchWidgets,
  onRemoveWidget,
  onMoveWidget,
}: CollectionManagerProps) {
  const [widgets, setWidgets] = useState<WidgetInCollection[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [movingWidgetId, setMovingWidgetId] = useState<string | null>(null);

  const loadWidgets = useCallback(async () => {
    if (!collectionId) return;
    setIsLoading(true);
    const result = await onFetchWidgets(collectionId, sessionId);
    setWidgets(result);
    setIsLoading(false);
  }, [collectionId, sessionId, onFetchWidgets]);

  useEffect(() => {
    setWidgets([]);
    loadWidgets();
  }, [loadWidgets]);

  async function handleRemove(widgetId: string) {
    if (!collectionId) return;
    const ok = await onRemoveWidget(collectionId, widgetId, sessionId);
    if (ok) setWidgets((prev) => prev.filter((w) => w.id !== widgetId));
  }

  async function handleMove(widgetId: string, targetCollectionId: string) {
    if (!collectionId) return;
    setMovingWidgetId(widgetId);
    const ok = await onMoveWidget(collectionId, targetCollectionId, widgetId, sessionId);
    setMovingWidgetId(null);
    if (ok) setWidgets((prev) => prev.filter((w) => w.id !== widgetId));
  }

  if (!collectionId) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Selecciona una colección para ver sus widgets.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Cargando widgets…
      </div>
    );
  }

  const otherCollections = collections.filter((c) => c.id !== collectionId);

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-foreground mb-1">
        Widgets ({widgets.length})
      </h3>

      {widgets.length === 0 && (
        <p className="text-xs text-muted-foreground py-4 text-center">
          Esta colección no tiene widgets guardados.
        </p>
      )}

      {widgets.map((widget) => (
        <div
          key={widget.id}
          data-role="collection-widget-item"
          data-widget-name={widget.display_name}
          data-widget-id={widget.id}
          className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2"
        >
          <span className="flex-1 text-sm truncate">{widget.display_name}</span>

          {otherCollections.length > 0 && (
            <select
              className="text-xs border border-input rounded px-1 py-0.5 bg-background text-foreground"
              defaultValue=""
              disabled={movingWidgetId === widget.id}
              onChange={(e) => {
                if (e.target.value) {
                  handleMove(widget.id, e.target.value);
                  e.target.value = "";
                }
              }}
              aria-label={`Mover ${widget.display_name} a colección`}
            >
              <option value="" disabled>
                Mover a…
              </option>
              {otherCollections.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}

          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive"
            onClick={() => handleRemove(widget.id)}
            aria-label={`Quitar ${widget.display_name} de la colección`}
          >
            ✕
          </Button>
        </div>
      ))}
    </div>
  );
}
