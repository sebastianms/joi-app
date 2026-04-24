"use client";

import { useCallback, useState } from "react";

const API_URL = "http://127.0.0.1:8000/api";

export interface Collection {
  id: string;
  session_id: string;
  name: string;
}

export interface WidgetInCollection {
  id: string;
  display_name: string;
  is_saved: boolean;
}

export interface SaveWidgetPayload {
  session_id: string;
  display_name: string;
  collection_ids: string[];
}

export interface UseCollectionsResult {
  collections: Collection[];
  isLoading: boolean;
  error: string | null;
  fetchCollections: (sessionId: string) => Promise<void>;
  createCollection: (sessionId: string, name: string) => Promise<Collection | null>;
  renameCollection: (collectionId: string, sessionId: string, name: string) => Promise<boolean>;
  deleteCollection: (collectionId: string, sessionId: string) => Promise<boolean>;
  fetchCollectionWidgets: (collectionId: string, sessionId: string) => Promise<WidgetInCollection[]>;
  addWidgetsToCollection: (collectionId: string, sessionId: string, widgetIds: string[]) => Promise<boolean>;
  removeWidgetFromCollection: (collectionId: string, widgetId: string, sessionId: string) => Promise<boolean>;
  saveWidget: (widgetId: string, payload: SaveWidgetPayload) => Promise<boolean>;
  unsaveWidget: (widgetId: string, sessionId: string) => Promise<boolean>;
}

export function useCollections(): UseCollectionsResult {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCollections = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/collections?session_id=${encodeURIComponent(sessionId)}`);
      if (!res.ok) throw new Error(`Failed to fetch collections: ${res.status}`);
      const data: Collection[] = await res.json();
      setCollections(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createCollection = useCallback(
    async (sessionId: string, name: string): Promise<Collection | null> => {
      setError(null);
      try {
        const res = await fetch(`${API_URL}/collections`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, name }),
        });
        if (!res.ok) throw new Error(`Failed to create collection: ${res.status}`);
        const created: Collection = await res.json();
        setCollections((prev) => [...prev, created]);
        return created;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return null;
      }
    },
    [],
  );

  const renameCollection = useCallback(
    async (collectionId: string, sessionId: string, name: string): Promise<boolean> => {
      setError(null);
      try {
        const res = await fetch(`${API_URL}/collections/${collectionId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, name }),
        });
        if (!res.ok) throw new Error(`Failed to rename collection: ${res.status}`);
        const updated: Collection = await res.json();
        setCollections((prev) => prev.map((c) => (c.id === collectionId ? updated : c)));
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return false;
      }
    },
    [],
  );

  const deleteCollection = useCallback(
    async (collectionId: string, sessionId: string): Promise<boolean> => {
      setError(null);
      try {
        const res = await fetch(
          `${API_URL}/collections/${collectionId}?session_id=${encodeURIComponent(sessionId)}`,
          { method: "DELETE" },
        );
        if (!res.ok) throw new Error(`Failed to delete collection: ${res.status}`);
        setCollections((prev) => prev.filter((c) => c.id !== collectionId));
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return false;
      }
    },
    [],
  );

  const fetchCollectionWidgets = useCallback(
    async (collectionId: string, sessionId: string): Promise<WidgetInCollection[]> => {
      try {
        const res = await fetch(
          `${API_URL}/collections/${collectionId}/widgets?session_id=${encodeURIComponent(sessionId)}`,
        );
        if (!res.ok) throw new Error(`Failed to fetch collection widgets: ${res.status}`);
        return await res.json();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return [];
      }
    },
    [],
  );

  const addWidgetsToCollection = useCallback(
    async (collectionId: string, sessionId: string, widgetIds: string[]): Promise<boolean> => {
      setError(null);
      try {
        const res = await fetch(`${API_URL}/collections/${collectionId}/widgets`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, widget_ids: widgetIds }),
        });
        if (!res.ok) throw new Error(`Failed to add widgets to collection: ${res.status}`);
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return false;
      }
    },
    [],
  );

  const removeWidgetFromCollection = useCallback(
    async (collectionId: string, widgetId: string, sessionId: string): Promise<boolean> => {
      setError(null);
      try {
        const res = await fetch(
          `${API_URL}/collections/${collectionId}/widgets/${widgetId}?session_id=${encodeURIComponent(sessionId)}`,
          { method: "DELETE" },
        );
        if (!res.ok) throw new Error(`Failed to remove widget from collection: ${res.status}`);
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return false;
      }
    },
    [],
  );

  const saveWidget = useCallback(
    async (widgetId: string, payload: SaveWidgetPayload): Promise<boolean> => {
      setError(null);
      try {
        const res = await fetch(`${API_URL}/widgets/${widgetId}/save`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`Failed to save widget: ${res.status}`);
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return false;
      }
    },
    [],
  );

  const unsaveWidget = useCallback(
    async (widgetId: string, sessionId: string): Promise<boolean> => {
      setError(null);
      try {
        const res = await fetch(
          `${API_URL}/widgets/${widgetId}/save?session_id=${encodeURIComponent(sessionId)}`,
          { method: "DELETE" },
        );
        if (!res.ok) throw new Error(`Failed to unsave widget: ${res.status}`);
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        return false;
      }
    },
    [],
  );

  return {
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
    saveWidget,
    unsaveWidget,
  };
}
