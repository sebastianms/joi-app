"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { DashboardGrid } from "@/components/dashboards/DashboardGrid";
import { useDashboards, type LayoutItemUpdate } from "@/hooks/useDashboards";
import { useCollections } from "@/hooks/use-collections";
import { getSessionId } from "@/lib/session";

export default function DashboardPage() {
  const params = useParams();
  const dashboardId = params.id as string;
  const [sessionId, setSessionId] = useState("");
  const [showAddWidget, setShowAddWidget] = useState(false);

  const { currentDashboard, isLoading, error, fetchDashboard, updateLayout, addItem, removeItem } =
    useDashboards();
  const { collections, fetchCollectionWidgets, fetchCollections } = useCollections();

  useEffect(() => {
    const sid = getSessionId();
    setSessionId(sid);
    fetchDashboard(dashboardId, sid);
  }, [dashboardId, fetchDashboard]);

  async function handleOpenAddWidget() {
    await fetchCollections(sessionId);
    setShowAddWidget(true);
  }

  async function handleAddWidget(widgetId: string) {
    const nextY = currentDashboard
      ? Math.max(0, ...currentDashboard.items.map((i) => i.grid_y + i.height))
      : 0;
    await addItem(dashboardId, {
      session_id: sessionId,
      widget_id: widgetId,
      grid_x: 0,
      grid_y: nextY,
      width: 6,
      height: 3,
    });
    setShowAddWidget(false);
  }

  async function handleLayoutChange(updates: LayoutItemUpdate[]) {
    await updateLayout(dashboardId, sessionId, updates);
  }

  async function handleRemoveItem(widgetId: string) {
    await removeItem(dashboardId, widgetId, sessionId);
  }

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">
        Cargando dashboard…
      </div>
    );
  }

  if (error || !currentDashboard) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-destructive">
        {error ?? "Dashboard no encontrado."}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background">
      <header className="flex items-center justify-between px-6 py-3 border-b border-border shrink-0">
        <h1 className="text-base font-semibold">{currentDashboard.name}</h1>
        <Button size="sm" onClick={handleOpenAddWidget}>
          + Añadir widget
        </Button>
      </header>

      <main className="flex-1 overflow-y-auto p-6">
        <DashboardGrid
          items={currentDashboard.items}
          onLayoutChange={handleLayoutChange}
          onRemoveItem={handleRemoveItem}
        />
      </main>

      {showAddWidget && (
        <AddWidgetPanel
          sessionId={sessionId}
          collections={collections}
          onFetchWidgets={fetchCollectionWidgets}
          onAdd={handleAddWidget}
          onClose={() => setShowAddWidget(false)}
        />
      )}
    </div>
  );
}

interface AddWidgetPanelProps {
  sessionId: string;
  collections: Array<{ id: string; name: string }>;
  onFetchWidgets: (colId: string, sessionId: string) => Promise<Array<{ id: string; display_name: string; is_saved: boolean }>>;
  onAdd: (widgetId: string) => Promise<void>;
  onClose: () => void;
}

function AddWidgetPanel({ sessionId, collections, onFetchWidgets, onAdd, onClose }: AddWidgetPanelProps) {
  const [selectedColId, setSelectedColId] = useState(collections[0]?.id ?? "");
  const [widgets, setWidgets] = useState<Array<{ id: string; display_name: string }>>([]);

  useEffect(() => {
    if (!selectedColId) return;
    onFetchWidgets(selectedColId, sessionId).then(setWidgets);
  }, [selectedColId, sessionId, onFetchWidgets]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-background border-t border-border w-full max-w-2xl rounded-t-lg p-5 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold">Añadir widget al dashboard</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>✕</Button>
        </div>

        {collections.length === 0 ? (
          <p className="text-xs text-muted-foreground">No tienes colecciones con widgets guardados.</p>
        ) : (
          <>
            <div className="flex gap-2 mb-3 flex-wrap">
              {collections.map((col) => (
                <button
                  key={col.id}
                  className={`px-3 py-1 rounded text-xs border ${
                    selectedColId === col.id
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border hover:bg-accent"
                  }`}
                  onClick={() => setSelectedColId(col.id)}
                >
                  {col.name}
                </button>
              ))}
            </div>
            <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
              {widgets.length === 0 && (
                <p className="text-xs text-muted-foreground">Esta colección no tiene widgets.</p>
              )}
              {widgets.map((w) => (
                <div
                  key={w.id}
                  className="flex items-center justify-between px-3 py-2 rounded border border-border"
                >
                  <span className="text-sm truncate">{w.display_name}</span>
                  <Button size="sm" variant="outline" onClick={() => onAdd(w.id)}>
                    Añadir
                  </Button>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
