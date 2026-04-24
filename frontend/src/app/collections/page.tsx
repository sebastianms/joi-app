"use client";

import { useEffect, useState } from "react";
import { CollectionList } from "@/components/collections/CollectionList";
import { CollectionManager } from "@/components/collections/CollectionManager";
import { useCollections } from "@/hooks/use-collections";

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  const existing = localStorage.getItem("joi_session_id");
  if (existing) return existing;
  const id = crypto.randomUUID();
  localStorage.setItem("joi_session_id", id);
  return id;
}

export default function CollectionsPage() {
  const [sessionId, setSessionId] = useState("");
  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(null);

  const {
    collections,
    isLoading,
    error,
    fetchCollections,
    createCollection,
    renameCollection,
    deleteCollection,
    fetchCollectionWidgets,
    addWidgetsToCollection,
    removeWidgetFromCollection,
  } = useCollections();

  useEffect(() => {
    const sid = getSessionId();
    setSessionId(sid);
    fetchCollections(sid);
  }, [fetchCollections]);

  async function handleCreate(name: string): Promise<boolean> {
    const created = await createCollection(sessionId, name);
    return created !== null;
  }

  async function handleRename(id: string, name: string): Promise<boolean> {
    return renameCollection(id, sessionId, name);
  }

  async function handleDelete(id: string): Promise<boolean> {
    const ok = await deleteCollection(id, sessionId);
    if (ok && selectedCollectionId === id) setSelectedCollectionId(null);
    return ok;
  }

  async function handleMoveWidget(
    fromCollectionId: string,
    toCollectionId: string,
    widgetId: string,
    sid: string,
  ): Promise<boolean> {
    const added = await addWidgetsToCollection(toCollectionId, sid, [widgetId]);
    if (!added) return false;
    return removeWidgetFromCollection(fromCollectionId, widgetId, sid);
  }

  return (
    <div className="flex h-screen">
      <aside className="w-64 border-r border-border bg-background p-4 overflow-y-auto shrink-0">
        {isLoading ? (
          <p className="text-xs text-muted-foreground">Cargando…</p>
        ) : (
          <CollectionList
            collections={collections}
            selectedId={selectedCollectionId}
            onSelect={setSelectedCollectionId}
            onRename={handleRename}
            onDelete={handleDelete}
            onCreate={handleCreate}
          />
        )}
        {error && (
          <p className="mt-2 text-xs text-destructive">{error}</p>
        )}
      </aside>

      <main className="flex-1 p-6 overflow-y-auto bg-background">
        <CollectionManager
          collectionId={selectedCollectionId}
          sessionId={sessionId}
          collections={collections}
          onFetchWidgets={fetchCollectionWidgets}
          onRemoveWidget={removeWidgetFromCollection}
          onMoveWidget={handleMoveWidget}
        />
      </main>
    </div>
  );
}
