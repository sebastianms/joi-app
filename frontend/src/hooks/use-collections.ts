"use client";

import { useCallback, useState } from "react";

const API_URL = "http://127.0.0.1:8000/api";

export interface Collection {
  id: string;
  session_id: string;
  name: string;
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

  return { collections, isLoading, error, fetchCollections, createCollection, saveWidget, unsaveWidget };
}
