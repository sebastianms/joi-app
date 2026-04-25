"use client";

import { useState } from "react";
import type { AgentTrace, DataExtraction } from "@/types/extraction";
import type { WidgetGenerationTrace } from "@/types/widget";

interface AgentTraceBlockProps {
  trace: AgentTrace;
  extraction?: DataExtraction;
}

export function AgentTraceBlock({ trace, extraction }: AgentTraceBlockProps) {
  const [open, setOpen] = useState(false);
  const rowCount = extraction?.row_count ?? trace.preview_rows.length;
  const ms = trace.widget_generation?.generation_ms ?? null;
  const summaryLabel = [
    ms != null ? `${ms}ms` : null,
    `${rowCount} fila${rowCount !== 1 ? "s" : ""}`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div
      className="mt-2 rounded-md border border-[color:var(--joi-border)] overflow-hidden text-xs"
      data-role="agent-trace"
      data-extraction-id={trace.extraction_id}
    >
      <button
        className="w-full flex items-center gap-2 px-3 py-2
          bg-[color:var(--joi-surface-elevated)] text-[color:var(--joi-muted)]
          hover:text-[color:var(--joi-text)] transition-colors text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label="Agent trace"
      >
        {/* Terminal icon */}
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="flex-shrink-0">
          <path d="M1.5 3L4.5 6L1.5 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M6 9h4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>

        {trace.security_rejection && (
          <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase
            bg-[color:var(--joi-accent-warm)]/20 text-[color:var(--joi-accent-warm)]">
            Rechazo de seguridad
          </span>
        )}

        <span className="font-mono tracking-tight">{trace.pipeline} — {summaryLabel}</span>
        <span className="ml-auto text-[10px]">{open ? "▼" : "▶"}</span>
      </button>

      {open && (
        <div
          className="border-t border-[color:var(--joi-border)] px-3 py-2 space-y-2
            bg-black/20"
        >
          {trace.query_display && (
            <SqlBlock sql={trace.query_display} />
          )}
          {trace.preview_rows.length > 0 && (
            <PreviewTable
              rows={trace.preview_rows}
              columns={trace.preview_columns.map((c) => c.name)}
            />
          )}
          {trace.widget_generation && (
            <WidgetGenerationSection wg={trace.widget_generation} />
          )}
        </div>
      )}
    </div>
  );
}

/* SQL keywords for inline highlight — no external lib */
const SQL_KEYWORDS =
  /\b(SELECT|FROM|WHERE|GROUP BY|ORDER BY|HAVING|JOIN|LEFT|RIGHT|INNER|OUTER|AS|ON|AND|OR|NOT|IN|LIKE|BETWEEN|IS|NULL|SUM|COUNT|AVG|MIN|MAX|DISTINCT|LIMIT|OFFSET|WITH|UNION|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|CASE|WHEN|THEN|ELSE|END|RETURNING)\b/gi;
const SQL_STRINGS = /('(?:[^'\\]|\\.)*')/g;

function SqlBlock({ sql }: { sql: string }) {
  // Two-pass highlight: strings first (to avoid keyword-coloring inside strings),
  // then keywords in non-string segments.
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  for (const strMatch of sql.matchAll(new RegExp(SQL_STRINGS.source, "g"))) {
    const before = sql.slice(lastIndex, strMatch.index);
    if (before) parts.push(...highlightKeywords(before, key));
    key += 100;
    parts.push(
      <span key={key++} className="text-[color:var(--joi-accent-warm)]">
        {strMatch[0]}
      </span>
    );
    lastIndex = strMatch.index! + strMatch[0].length;
  }
  const tail = sql.slice(lastIndex);
  if (tail) parts.push(...highlightKeywords(tail, key));

  return (
    <pre
      className="overflow-x-auto rounded bg-black/30 p-2 font-mono text-[11px]
        leading-relaxed whitespace-pre-wrap text-[color:var(--joi-muted)]"
    >
      {parts}
    </pre>
  );
}

function highlightKeywords(text: string, baseKey: number): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let k = baseKey;
  for (const m of text.matchAll(new RegExp(SQL_KEYWORDS.source, "gi"))) {
    if (m.index! > last) nodes.push(text.slice(last, m.index));
    nodes.push(
      <span key={k++} className="text-[color:var(--joi-accent)] font-semibold">
        {m[0]}
      </span>
    );
    last = m.index! + m[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

const STATUS_CONFIG: Record<
  WidgetGenerationTrace["status"],
  { label: string; cls: string }
> = {
  success: {
    label: "LISTO",
    cls: "bg-[color:var(--joi-success)]/15 text-[color:var(--joi-success)]",
  },
  fallback: {
    label: "FALLBACK",
    cls: "bg-[color:var(--joi-accent-warm)]/15 text-[color:var(--joi-accent-warm)]",
  },
  error: {
    label: "ERROR",
    cls: "bg-[color:var(--joi-accent-warm)]/20 text-[color:var(--joi-accent-warm)]",
  },
};

function WidgetGenerationSection({ wg }: { wg: WidgetGenerationTrace }) {
  const cfg = STATUS_CONFIG[wg.status];
  const isPending = wg.status === "success" && wg.generation_ms === 0;

  return (
    <div
      className="rounded-md border border-[color:var(--joi-border)]
        bg-[color:var(--joi-surface-elevated)]/60 p-2 font-mono text-[11px] leading-relaxed"
      data-role="widget-generation-trace"
      data-status={wg.status}
      data-widget-type={wg.widget_type_attempted}
    >
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <span className="font-semibold text-[color:var(--joi-text)]">Widget</span>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${cfg.cls}
            ${isPending ? "[animation:pulse-accent_2s_infinite]" : ""}`}
        >
          {cfg.label}
        </span>
        {wg.widget_type_attempted && (
          <span className="text-[color:var(--joi-muted)]">{wg.widget_type_attempted}</span>
        )}
        {wg.generation_ms > 0 && (
          <span className="text-[color:var(--joi-muted)]">{wg.generation_ms}ms</span>
        )}
        {wg.error_code && (
          <span className="text-[color:var(--joi-accent-warm)]">{wg.error_code}</span>
        )}
      </div>
      {wg.generated_by_model && (
        <div className="text-[color:var(--joi-muted)]">model: {wg.generated_by_model}</div>
      )}
      {wg.message && (
        <div className="whitespace-pre-wrap break-words text-[color:var(--joi-text)] mt-1">
          {wg.message}
        </div>
      )}
    </div>
  );
}

interface PreviewTableProps {
  rows: Record<string, unknown>[];
  columns: string[];
}

function PreviewTable({ rows, columns }: PreviewTableProps) {
  const cols = columns.length > 0 ? columns : Object.keys(rows[0] ?? {});

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left font-mono text-[11px]">
        <thead>
          <tr>
            {cols.map((col) => (
              <th
                key={col}
                className="border-b border-[color:var(--joi-border)] px-2 py-1
                  text-[color:var(--joi-muted)] font-medium uppercase tracking-wider text-[10px]"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-[color:var(--joi-border)]/50
                even:bg-white/[0.02] text-[color:var(--joi-text)]"
            >
              {cols.map((col) => (
                <td key={col} className="px-2 py-1">
                  {String(row[col] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
