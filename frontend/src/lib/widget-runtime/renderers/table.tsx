// Table renderer (T121).
// Universal fallback: always applicable. Rendered with inline styles so it
// works regardless of the parent page's stylesheet (iframe CSP blocks
// cross-origin fetches anyway).

import type { CSSProperties } from "react";
import { registerRenderer, type RendererProps } from "../registry";

const CONTAINER: CSSProperties = {
  fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif",
  fontSize: "14px",
  color: "#111827",
  padding: "16px",
};

const HEADER: CSSProperties = {
  marginBottom: "12px",
};

const TITLE: CSSProperties = {
  margin: 0,
  fontSize: "16px",
  fontWeight: 600,
};

const SUBTITLE: CSSProperties = {
  margin: "4px 0 0",
  fontSize: "12px",
  color: "#6b7280",
};

const TABLE_WRAP: CSSProperties = {
  overflowX: "auto",
  borderRadius: "8px",
  border: "1px solid #e5e7eb",
};

const TABLE: CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
};

const TH: CSSProperties = {
  textAlign: "left",
  padding: "10px 12px",
  borderBottom: "1px solid #e5e7eb",
  background: "#f9fafb",
  fontWeight: 600,
  fontSize: "13px",
  color: "#374151",
};

const TD: CSSProperties = {
  padding: "10px 12px",
  borderBottom: "1px solid #f3f4f6",
  verticalAlign: "top",
};

const BADGE: CSSProperties = {
  display: "inline-block",
  marginLeft: "8px",
  padding: "2px 8px",
  borderRadius: "9999px",
  background: "#fef3c7",
  color: "#92400e",
  fontSize: "11px",
  fontWeight: 500,
};

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function TableRenderer({ spec, rows }: RendererProps) {
  const columns = spec.data_reference.columns;
  const title = spec.visual_options?.title;
  const subtitle = spec.visual_options?.subtitle;

  return (
    <div style={CONTAINER}>
      {(title || spec.truncation_badge) && (
        <div style={HEADER}>
          {title && (
            <h2 style={TITLE}>
              {title}
              {spec.truncation_badge && <span style={BADGE}>resultado truncado</span>}
            </h2>
          )}
          {!title && spec.truncation_badge && (
            <span style={BADGE}>resultado truncado</span>
          )}
          {subtitle && <p style={SUBTITLE}>{subtitle}</p>}
        </div>
      )}

      <div style={TABLE_WRAP}>
        <table style={TABLE}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.name} style={TH}>
                  {col.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx}>
                {columns.map((col) => (
                  <td key={col.name} style={TD}>
                    {formatCell(row[col.name])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

registerRenderer("table", TableRenderer);
