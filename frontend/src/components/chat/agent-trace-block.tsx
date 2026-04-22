"use client";

import type { AgentTrace, DataExtraction } from "@/types/extraction";

interface AgentTraceBlockProps {
  trace: AgentTrace;
  extraction?: DataExtraction;
}

export function AgentTraceBlock({ trace, extraction }: AgentTraceBlockProps) {
  const rowCount = extraction?.row_count ?? trace.preview_rows.length;
  const summaryLabel = `Agent Trace — ${trace.pipeline} — ${rowCount} fila${rowCount !== 1 ? "s" : ""}`;

  return (
    <details
      className="mt-1 w-full rounded-md border border-border bg-background text-xs"
      data-role="agent-trace"
      aria-label="Agent trace"
    >
      <summary className="flex cursor-pointer select-none items-center gap-2 px-3 py-2 font-mono text-muted-foreground hover:text-foreground">
        {trace.security_rejection && (
          <span className="rounded bg-destructive px-1.5 py-0.5 text-[10px] font-semibold uppercase text-destructive-foreground">
            Rechazo de seguridad
          </span>
        )}
        {summaryLabel}
      </summary>

      <div className="border-t border-border px-3 py-2 space-y-2">
        {trace.query_display && (
          <pre className="overflow-x-auto rounded bg-muted p-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
            {trace.query_display}
          </pre>
        )}

        {trace.preview_rows.length > 0 && (
          <PreviewTable
            rows={trace.preview_rows}
            columns={trace.preview_columns.map((c) => c.name)}
          />
        )}
      </div>
    </details>
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
                className="border-b border-border px-2 py-1 text-muted-foreground"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="even:bg-muted/40">
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
