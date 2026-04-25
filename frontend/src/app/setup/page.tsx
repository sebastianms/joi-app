"use client";

import { useState } from "react";
import { SetupShell } from "@/components/setup/SetupShell";
import { SQLConnectionForm } from "@/components/setup/sql-form";
import { JSONUploadForm } from "@/components/setup/json-form";
import { VectorStoreStep } from "@/components/setup/VectorStoreStep";
import { RenderModeStep } from "@/components/setup/RenderModeStep";
import { useRenderMode } from "@/hooks/useRenderMode";
import { joiStorage } from "@/lib/storage/joi-storage";

type Tab = "sql" | "json" | "vector-store" | "render-mode";

const TABS: { id: Tab; label: string }[] = [
  { id: "sql", label: "SQL" },
  { id: "json", label: "JSON" },
  { id: "vector-store", label: "Vector Store" },
  { id: "render-mode", label: "Widgets" },
];

export default function SetupPage() {
  const [activeTab, setActiveTab] = useState<Tab>("sql");
  const sessionId = joiStorage.sessionId.get();
  const { mode, setMode, isSaving, error } = useRenderMode(sessionId);

  return (
    <SetupShell>
      {/* Tab bar */}
      <div
        role="tablist"
        className="flex gap-1 mb-6 p-1 rounded-xl bg-[color:var(--joi-surface-elevated)] border border-[color:var(--joi-border)]"
      >
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            aria-selected={activeTab === id}
            onClick={() => setActiveTab(id)}
            className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition-all
              ${activeTab === id
                ? "bg-[color:var(--joi-accent)] text-black shadow"
                : "text-[color:var(--joi-muted)] hover:text-[color:var(--joi-text)]"
              }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Panels */}
      <div
        className="rounded-2xl border border-[color:var(--joi-border)]
          bg-[color:var(--joi-surface-elevated)]/80 backdrop-blur-md p-6"
      >
        {activeTab === "sql" && <SQLConnectionForm />}
        {activeTab === "json" && <JSONUploadForm />}
        {activeTab === "vector-store" && <VectorStoreStep />}
        {activeTab === "render-mode" && (
          <RenderModeStep
            value={mode}
            onChange={(m) => { void setMode(m); }}
            isSaving={isSaving}
            error={error}
          />
        )}
      </div>
    </SetupShell>
  );
}
