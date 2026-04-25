"use client";

import { useState } from "react";
import { joiStorage } from "@/lib/storage/joi-storage";

type SourceType = "POSTGRESQL" | "MYSQL" | "SQLITE";

const INPUT_CLS = `w-full rounded-lg px-3 py-2.5 text-sm
  bg-black/30 border border-[color:var(--joi-border)]
  text-[color:var(--joi-text)] placeholder:text-[color:var(--joi-muted)]
  focus:outline-none focus:border-[color:var(--joi-accent)]
  focus:shadow-[0_0_0_3px_var(--joi-glow)]
  transition-all`;

const LABEL_CLS = "block text-xs font-medium text-[color:var(--joi-muted)] mb-1.5 uppercase tracking-wider";

export function SQLConnectionForm() {
  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("POSTGRESQL");
  const [connectionString, setConnectionString] = useState("");
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("idle");
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";
      const sessionId = joiStorage.sessionId.get() ?? "demo-session";
      const r = await fetch(`${baseUrl}/connections/sql`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          source_type: sourceType,
          connection_string: connectionString,
          user_session_id: sessionId,
        }),
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail ?? "Error desconocido");
      }
      setStatus("success");
    } catch (e) {
      setStatus("error");
      setErrorMessage(e instanceof Error ? e.message : "Error inesperado");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={(e) => { void handleSubmit(e); }} className="space-y-5">
      <div>
        <label className={LABEL_CLS}>Nombre de la conexión</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Producción DB"
          required
          minLength={2}
          className={INPUT_CLS}
        />
      </div>

      <div>
        <label className={LABEL_CLS}>Motor</label>
        <select
          value={sourceType}
          onChange={(e) => setSourceType(e.target.value as SourceType)}
          className={INPUT_CLS}
          style={{ appearance: "none" }}
        >
          <option value="POSTGRESQL">PostgreSQL</option>
          <option value="MYSQL">MySQL</option>
          <option value="SQLITE">SQLite</option>
        </select>
      </div>

      <div>
        <label className={LABEL_CLS}>Connection string</label>
        <input
          value={connectionString}
          onChange={(e) => setConnectionString(e.target.value)}
          placeholder="postgresql+asyncpg://user:pass@host/db"
          required
          minLength={5}
          className={INPUT_CLS}
        />
      </div>

      {status === "success" && (
        <div
          className="flex items-center gap-2 rounded-lg px-4 py-3 text-sm
            border border-[color:var(--joi-success)]/30
            bg-[color:var(--joi-success)]/10
            text-[color:var(--joi-success)]"
        >
          <span>✓</span> Conexión establecida correctamente.
        </div>
      )}

      {status === "error" && (
        <div
          className="flex items-center gap-2 rounded-lg px-4 py-3 text-sm
            border border-[color:var(--joi-accent-warm)]/30
            bg-[color:var(--joi-accent-warm)]/10
            text-[color:var(--joi-accent-warm)]"
        >
          <span>⚠</span> {errorMessage}
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-2.5 rounded-lg text-sm font-semibold
          bg-[color:var(--joi-accent)] text-black
          hover:opacity-90 transition-opacity
          disabled:opacity-50"
      >
        {isSubmitting ? "Conectando…" : "Conectar"}
      </button>
    </form>
  );
}
