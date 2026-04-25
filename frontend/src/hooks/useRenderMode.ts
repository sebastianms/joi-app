"use client";

import { useCallback, useEffect, useState } from "react";
import { joiStorage } from "@/lib/storage/joi-storage";

export type RenderMode = "shadcn" | "bootstrap" | "heroui" | "design_system_disabled";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

function backendToFrontend(mode: string, ui_library: string | null): RenderMode {
  if (mode === "free_code") return "design_system_disabled";
  if (ui_library === "bootstrap") return "bootstrap";
  if (ui_library === "heroui") return "heroui";
  return "shadcn";
}

function frontendToBackend(mode: RenderMode): { mode: string; ui_library: string | null } {
  if (mode === "design_system_disabled") return { mode: "free_code", ui_library: null };
  return { mode: "ui_framework", ui_library: mode };
}

export function useRenderMode(sessionId: string | null) {
  const [mode, setModeState] = useState<RenderMode>(() => {
    const cached = joiStorage.renderMode.get();
    return cached ?? "shadcn";
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    setIsLoading(true);
    fetch(`${API_BASE}/render-mode/${sessionId}`)
      .then((r) => r.json())
      .then((data) => {
        const resolved = backendToFrontend(data.mode, data.ui_library);
        setModeState(resolved);
        joiStorage.renderMode.set(resolved);
      })
      .catch(() => {
        // keep localStorage cache as fallback
      })
      .finally(() => setIsLoading(false));
  }, [sessionId]);

  const setMode = useCallback(
    async (next: RenderMode) => {
      if (!sessionId) return;
      setError(null);
      setIsSaving(true);
      const body = frontendToBackend(next);
      try {
        const r = await fetch(`${API_BASE}/render-mode/${sessionId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error("Error guardando render-mode");
        const data = await r.json();
        const resolved = backendToFrontend(data.mode, data.ui_library);
        setModeState(resolved);
        joiStorage.renderMode.set(resolved);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error desconocido");
      } finally {
        setIsSaving(false);
      }
    },
    [sessionId],
  );

  return { mode, setMode, isLoading, isSaving, error };
}
