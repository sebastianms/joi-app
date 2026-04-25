"use client";

import { useState } from "react";
import { joiStorage } from "@/lib/storage/joi-storage";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

const INPUT_CLS = `w-full rounded-lg px-3 py-2.5 text-sm
  bg-black/30 border border-[color:var(--joi-border)]
  text-[color:var(--joi-text)] placeholder:text-[color:var(--joi-muted)]
  focus:outline-none focus:border-[color:var(--joi-accent)]
  focus:shadow-[0_0_0_3px_var(--joi-glow)]
  transition-all`;

const LABEL_CLS = "block text-xs font-medium text-[color:var(--joi-muted)] mb-1.5 uppercase tracking-wider";

export function JSONUploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [connectionName, setConnectionName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null;
    setError(null);
    setSuccess(null);
    if (!selected) { setFile(null); return; }
    if (selected.size > MAX_FILE_SIZE) {
      setError("Archivo demasiado grande. Máximo 10 MB.");
      setFile(null);
      e.target.value = "";
      return;
    }
    if (selected.type !== "application/json" && !selected.name.endsWith(".json")) {
      setError("Solo se permiten archivos .json.");
      setFile(null);
      e.target.value = "";
      return;
    }
    setFile(selected);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !connectionName) return;
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("name", connectionName);
      formData.append("user_session_id", joiStorage.sessionId.get() ?? "demo-session");

      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";
      const r = await fetch(`${apiUrl}/connections/json`, { method: "POST", body: formData });
      const data = await r.json() as { detail?: string };
      if (!r.ok) throw new Error(data.detail ?? "Error subiendo archivo");

      setSuccess("Archivo cargado y validado correctamente.");
      setFile(null);
      setConnectionName("");
      (e.target as HTMLFormElement).reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <form onSubmit={(e) => { void onSubmit(e); }} className="space-y-5">
      <div>
        <label className={LABEL_CLS}>Nombre de la conexión</label>
        <input
          value={connectionName}
          onChange={(e) => setConnectionName(e.target.value)}
          placeholder="Datos históricos de ventas"
          required
          disabled={isLoading}
          className={INPUT_CLS}
        />
      </div>

      <div>
        <label className={LABEL_CLS}>Archivo JSON</label>
        <input
          type="file"
          accept=".json,application/json"
          onChange={handleFileChange}
          required
          disabled={isLoading}
          className={`${INPUT_CLS} cursor-pointer file:mr-3 file:rounded file:border-0
            file:bg-[color:var(--joi-accent)] file:text-black file:text-xs file:font-semibold file:px-3 file:py-1`}
        />
        <p className="text-[10px] text-[color:var(--joi-muted)] mt-1.5">Máximo 10 MB · formato .json</p>
      </div>

      {success && (
        <div className="flex items-center gap-2 rounded-lg px-4 py-3 text-sm
          border border-[color:var(--joi-success)]/30 bg-[color:var(--joi-success)]/10 text-[color:var(--joi-success)]">
          <span>✓</span> {success}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg px-4 py-3 text-sm
          border border-[color:var(--joi-accent-warm)]/30 bg-[color:var(--joi-accent-warm)]/10 text-[color:var(--joi-accent-warm)]">
          <span>⚠</span> {error}
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading || !file || !connectionName}
        className="w-full py-2.5 rounded-lg text-sm font-semibold
          bg-[color:var(--joi-accent)] text-black
          hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {isLoading ? "Subiendo…" : "Subir archivo"}
      </button>
    </form>
  );
}
