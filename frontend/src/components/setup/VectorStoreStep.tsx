"use client";

import { useEffect, useState } from "react";
import { CheckCircle, AlertCircle, Database } from "lucide-react";
import { type VectorStoreProvider, useVectorStoreConfig } from "@/hooks/useVectorStoreConfig";
import { getSessionId } from "@/lib/session";

const PROVIDERS: { value: VectorStoreProvider; label: string }[] = [
  { value: "qdrant", label: "Qdrant (externo)" },
  { value: "chroma", label: "Chroma" },
  { value: "pinecone", label: "Pinecone" },
  { value: "weaviate", label: "Weaviate" },
  { value: "pgvector", label: "PGVector (PostgreSQL)" },
];

const PROVIDER_FIELDS: Record<VectorStoreProvider, { key: string; label: string; placeholder: string }[]> = {
  qdrant: [
    { key: "url", label: "URL", placeholder: "http://localhost:6333" },
    { key: "api_key", label: "API Key (opcional)", placeholder: "" },
  ],
  chroma: [
    { key: "host", label: "Host", placeholder: "localhost" },
    { key: "port", label: "Port", placeholder: "8000" },
  ],
  pinecone: [
    { key: "api_key", label: "API Key", placeholder: "" },
    { key: "index_name", label: "Index Name", placeholder: "widget-cache" },
  ],
  weaviate: [
    { key: "http_host", label: "HTTP Host", placeholder: "localhost" },
    { key: "http_port", label: "HTTP Port", placeholder: "8080" },
    { key: "grpc_host", label: "gRPC Host", placeholder: "localhost" },
    { key: "grpc_port", label: "gRPC Port", placeholder: "50051" },
  ],
  pgvector: [
    { key: "connection_string", label: "Connection String", placeholder: "postgresql+psycopg://user:pass@host/db" },
  ],
};

export function VectorStoreStep() {
  const sessionId = getSessionId();
  const { config, isLoading, error, validating, saving, fetchConfig, validateConfig, saveConfig, deleteConfig } =
    useVectorStoreConfig();

  const [provider, setProvider] = useState<VectorStoreProvider>("qdrant");
  const [params, setParams] = useState<Record<string, string>>({});
  const [validated, setValidated] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    void fetchConfig(sessionId);
  }, [fetchConfig, sessionId]);

  function handleProviderChange(p: VectorStoreProvider) {
    setProvider(p);
    setParams({});
    setValidated(false);
    setSaveSuccess(false);
  }

  function handleParamChange(key: string, value: string) {
    setParams((prev) => ({ ...prev, [key]: value }));
    setValidated(false);
  }

  async function handleValidate() {
    const ok = await validateConfig(provider, params);
    setValidated(ok);
  }

  async function handleSave() {
    await saveConfig(sessionId, provider, params);
    setSaveSuccess(true);
  }

  async function handleDelete() {
    await deleteConfig(sessionId);
    setSaveSuccess(false);
    setValidated(false);
  }

  const fields = PROVIDER_FIELDS[provider];

  return (
    <div className="space-y-5">
      {!config || config.is_default ? (
        <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300">
          <Database className="h-4 w-4 shrink-0" />
          Usando Qdrant interno por defecto. Configura tu propio proveedor abajo (opcional).
        </div>
      ) : (
        <div className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm dark:border-green-800 dark:bg-green-950">
          <span className="flex items-center gap-2 text-green-700 dark:text-green-300">
            <CheckCircle className="h-4 w-4" />
            Proveedor activo: <strong>{config.provider}</strong>
          </span>
          <button
            className="text-xs text-red-600 underline hover:opacity-80 dark:text-red-400"
            onClick={() => void handleDelete()}
          >
            Eliminar
          </button>
        </div>
      )}

      {isLoading && <p className="text-sm text-muted-foreground">Cargando configuración…</p>}

      <div>
        <label className="mb-1 block text-sm font-medium">Proveedor</label>
        <select
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
          value={provider}
          onChange={(e) => handleProviderChange(e.target.value as VectorStoreProvider)}
        >
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {fields.map((f) => (
        <div key={f.key}>
          <label className="mb-1 block text-sm font-medium">{f.label}</label>
          <input
            type={f.key.toLowerCase().includes("key") || f.key.toLowerCase().includes("password") ? "password" : "text"}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            placeholder={f.placeholder}
            value={params[f.key] ?? ""}
            onChange={(e) => handleParamChange(f.key, e.target.value)}
          />
        </div>
      ))}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {validated && !error && (
        <p className="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
          <CheckCircle className="h-4 w-4" /> Conexión validada correctamente
        </p>
      )}

      {saveSuccess && (
        <p className="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
          <CheckCircle className="h-4 w-4" /> Configuración guardada
        </p>
      )}

      <div className="flex gap-2">
        <button
          className="rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
          disabled={validating}
          onClick={() => void handleValidate()}
        >
          {validating ? "Validando…" : "Validar conexión"}
        </button>
        <button
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          disabled={!validated || saving}
          onClick={() => void handleSave()}
        >
          {saving ? "Guardando…" : "Guardar"}
        </button>
      </div>
    </div>
  );
}
