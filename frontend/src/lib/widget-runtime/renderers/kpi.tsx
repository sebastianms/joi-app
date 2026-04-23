// KPI renderer (T125).
// Single big number from row 0, column bindings.value. Optional bindings.label
// appears as a muted caption. Applicability ensures exactly 1 row + 1 numeric.

import type { CSSProperties } from "react";
import { registerRenderer, type RendererProps } from "../registry";
import { ChartFrame } from "./_chart-frame";

const WRAP: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  padding: "24px 16px",
  minHeight: "180px",
};

const VALUE: CSSProperties = {
  fontSize: "44px",
  fontWeight: 700,
  color: "#111827",
  lineHeight: 1.1,
  letterSpacing: "-0.02em",
};

const CAPTION: CSSProperties = {
  marginTop: "8px",
  fontSize: "13px",
  color: "#6b7280",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

function formatKpi(value: unknown, hint?: string): string {
  if (value === null || value === undefined) return "—";
  if (typeof value !== "number") return String(value);
  if (hint === "percent") return `${value.toFixed(1)}%`;
  if (hint === "currency") {
    return new Intl.NumberFormat("es", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    }).format(value);
  }
  if (hint === "integer") return value.toLocaleString("es");
  return value.toLocaleString("es", { maximumFractionDigits: 2 });
}

function KpiRenderer({ spec, rows }: RendererProps) {
  const { value: valueKey, label: labelKey } = spec.bindings;
  if (!valueKey || rows.length === 0) {
    return (
      <ChartFrame spec={spec}>
        <p style={{ color: "#6b7280" }}>
          El widget no declaró bindings.value o la extracción está vacía.
        </p>
      </ChartFrame>
    );
  }

  const row = rows[0];
  const rawValue = row[valueKey];
  const caption = labelKey ? String(row[labelKey] ?? valueKey) : valueKey;
  const hint =
    spec.visual_options?.format_hints?.[valueKey] ?? spec.visual_options?.value_format;

  return (
    <ChartFrame spec={spec}>
      <div style={WRAP}>
        <div style={VALUE}>{formatKpi(rawValue, hint)}</div>
        <div style={CAPTION}>{caption}</div>
      </div>
    </ChartFrame>
  );
}

registerRenderer("kpi", KpiRenderer);
