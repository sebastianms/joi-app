"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useDashboards } from "@/hooks/useDashboards";
import { getSessionId } from "@/lib/session";
import { AppHeader } from "@/components/layout/AppHeader";

export default function DashboardsPage() {
  const [sessionId, setSessionId] = useState("");
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const { dashboards, isLoading, error, fetchDashboards, createDashboard, deleteDashboard } =
    useDashboards();

  useEffect(() => {
    const sid = getSessionId();
    setSessionId(sid);
    fetchDashboards(sid);
  }, [fetchDashboards]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    await createDashboard(sessionId, name);
    setNewName("");
    setCreating(false);
  }

  return (
    <div className="flex flex-col min-h-screen">
      <AppHeader />
    <main className="flex flex-col flex-1 p-8 max-w-2xl mx-auto w-full">
      <h1 className="text-xl font-bold tracking-tight mb-6 text-[color:var(--joi-text)]">
        Dashboards
      </h1>

      <form onSubmit={handleCreate} className="flex gap-2 mb-8">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Nombre del dashboard…"
          className="flex-1 rounded-lg px-3 py-2 text-sm
            bg-black/30 border border-[color:var(--joi-border)]
            text-[color:var(--joi-text)] placeholder:text-[color:var(--joi-muted)]
            focus:outline-none focus:border-[color:var(--joi-accent)]"
          aria-label="Nombre del dashboard"
        />
        <button
          type="submit"
          disabled={creating || newName.trim().length === 0}
          className="px-4 py-2 rounded-lg text-sm font-semibold
            bg-[color:var(--joi-accent)] text-black
            hover:opacity-90 transition-opacity
            disabled:opacity-40 disabled:cursor-not-allowed"
        >
          + Crear
        </button>
      </form>

      {isLoading && (
        <p className="text-sm text-[color:var(--joi-muted)]">Cargando…</p>
      )}

      {error && (
        <p className="text-sm text-destructive mb-4">{error}</p>
      )}

      {!isLoading && dashboards.length === 0 && (
        <p className="text-sm text-[color:var(--joi-muted)]">
          No tienes dashboards todavía. Crea uno arriba.
        </p>
      )}

      <ul className="flex flex-col gap-2">
        {dashboards.map((d) => (
          <li
            key={d.id}
            className="flex items-center justify-between rounded-xl px-4 py-3
              border border-[color:var(--joi-border)]
              bg-[color:var(--joi-surface)] hover:border-[color:var(--joi-accent)]/40
              transition-colors"
            data-role="dashboard-item"
            data-dashboard-id={d.id}
          >
            <Link
              href={`/dashboards/${d.id}`}
              className="flex-1 text-sm font-medium text-[color:var(--joi-text)] hover:text-[color:var(--joi-accent)] transition-colors"
            >
              {d.name}
            </Link>
            <button
              onClick={() => deleteDashboard(d.id, sessionId)}
              aria-label={`Eliminar dashboard ${d.name}`}
              className="ml-4 text-xs text-[color:var(--joi-muted)] hover:text-destructive transition-colors px-2 py-1"
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </main>
    </div>
  );
}
