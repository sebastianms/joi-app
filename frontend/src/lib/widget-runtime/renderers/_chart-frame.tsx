// Shared layout scaffold for chart renderers (T122-T128).
// Keeps the header (title/subtitle/badge) and responsive container wrapper
// consistent across bar/line/pie/scatter/area/heatmap so each renderer
// focuses only on the chart body.

import type { CSSProperties, ReactNode } from "react";
import type { WidgetSpec } from "@/types/widget";

const CONTAINER: CSSProperties = {
  fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif",
  fontSize: "14px",
  color: "#111827",
  padding: "16px",
  display: "flex",
  flexDirection: "column",
  gap: "12px",
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

const BODY: CSSProperties = {
  width: "100%",
  minHeight: "280px",
};

export const CHART_COLORS = [
  "#2563eb",
  "#16a34a",
  "#dc2626",
  "#ca8a04",
  "#9333ea",
  "#0891b2",
  "#ea580c",
  "#4f46e5",
];

interface ChartFrameProps {
  spec: WidgetSpec;
  children: ReactNode;
}

export function ChartFrame({ spec, children }: ChartFrameProps) {
  const { title, subtitle } = spec.visual_options ?? {};
  const showHeader = Boolean(title) || spec.truncation_badge || Boolean(subtitle);

  return (
    <div style={CONTAINER}>
      {showHeader && (
        <div>
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
      <div style={BODY}>{children}</div>
    </div>
  );
}
