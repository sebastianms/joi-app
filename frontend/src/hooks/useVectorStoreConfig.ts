"use client";

import { useCallback, useState } from "react";

const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

export type VectorStoreProvider = "qdrant" | "chroma" | "pinecone" | "weaviate" | "pgvector";

export interface VectorStoreConfig {
  id: string;
  session_id: string;
  provider: string;
  is_default: boolean;
  last_validated_at: string | null;
  created_at: string | null;
}

export interface UseVectorStoreConfigResult {
  config: VectorStoreConfig | null;
  isLoading: boolean;
  error: string | null;
  validating: boolean;
  saving: boolean;
  fetchConfig: (sessionId: string) => Promise<void>;
  validateConfig: (provider: VectorStoreProvider, params: Record<string, string>) => Promise<boolean>;
  saveConfig: (sessionId: string, provider: VectorStoreProvider, params: Record<string, string>) => Promise<void>;
  deleteConfig: (sessionId: string) => Promise<void>;
}

export function useVectorStoreConfig(): UseVectorStoreConfigResult {
  const [config, setConfig] = useState<VectorStoreConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConfig = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${DEFAULT_API_URL}/vector-store/config?session_id=${encodeURIComponent(sessionId)}`);
      if (!res.ok) throw new Error("Error al obtener configuración");
      const data = await res.json() as VectorStoreConfig | null;
      setConfig(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const validateConfig = useCallback(
    async (provider: VectorStoreProvider, params: Record<string, string>): Promise<boolean> => {
      setValidating(true);
      setError(null);
      try {
        const res = await fetch(`${DEFAULT_API_URL}/vector-store/validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ provider, connection_params: params }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({})) as { detail?: string };
          throw new Error(data.detail ?? "Validación fallida");
        }
        return true;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error desconocido");
        return false;
      } finally {
        setValidating(false);
      }
    },
    []
  );

  const saveConfig = useCallback(
    async (sessionId: string, provider: VectorStoreProvider, params: Record<string, string>) => {
      setSaving(true);
      setError(null);
      try {
        const res = await fetch(`${DEFAULT_API_URL}/vector-store/config`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, provider, connection_params: params }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({})) as { detail?: string };
          throw new Error(data.detail ?? "Error al guardar configuración");
        }
        const saved = await res.json() as VectorStoreConfig;
        setConfig(saved);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error desconocido");
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const deleteConfig = useCallback(async (sessionId: string) => {
    setError(null);
    try {
      const res = await fetch(
        `${DEFAULT_API_URL}/vector-store/config?session_id=${encodeURIComponent(sessionId)}`,
        { method: "DELETE" }
      );
      if (!res.ok && res.status !== 404) throw new Error("Error al eliminar configuración");
      setConfig(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    }
  }, []);

  return { config, isLoading, error, validating, saving, fetchConfig, validateConfig, saveConfig, deleteConfig };
}
