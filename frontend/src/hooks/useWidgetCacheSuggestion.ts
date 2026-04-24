"use client";

import { useCallback, useState } from "react";

const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

export interface UseWidgetCacheSuggestionResult {
  isReusing: boolean;
  reuseError: string | null;
  reuseCache: (cacheEntryId: string, sessionId: string) => Promise<void>;
}

export function useWidgetCacheSuggestion(
  onReuseSuccess?: () => void
): UseWidgetCacheSuggestionResult {
  const [isReusing, setIsReusing] = useState(false);
  const [reuseError, setReuseError] = useState<string | null>(null);

  const reuseCache = useCallback(
    async (cacheEntryId: string, sessionId: string): Promise<void> => {
      setIsReusing(true);
      setReuseError(null);
      try {
        const response = await fetch(
          `${DEFAULT_API_URL}/widget-cache/${cacheEntryId}/reuse`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId }),
          }
        );
        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail ?? "Error al reutilizar cache");
        }
        onReuseSuccess?.();
      } catch (err) {
        setReuseError(err instanceof Error ? err.message : "Error desconocido");
      } finally {
        setIsReusing(false);
      }
    },
    [onReuseSuccess]
  );

  return { isReusing, reuseError, reuseCache };
}
