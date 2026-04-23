// Heatmap renderer (T127, R5).
// Custom SVG matrix (no Recharts primitive). Axes are two small-cardinality
// categoricals (x/y), cell color encodes the numeric value.

import type { CSSProperties } from "react";
import type { WidgetSpec } from "@/types/widget";
import { registerRenderer, type RendererProps } from "../registry";
import { ChartFrame } from "./_chart-frame";

const CELL_SIZE = 48;
const AXIS_PADDING = 64;
const LEGEND_HEIGHT = 24;
const MIN_LUMINOSITY = 92;
const MAX_LUMINOSITY = 32;

const AXIS_LABEL_STYLE: CSSProperties = {
  fontSize: "11px",
  fill: "#374151",
};

const CELL_LABEL_STYLE: CSSProperties = {
  fontSize: "10px",
  fill: "#f9fafb",
  textAnchor: "middle",
  dominantBaseline: "middle",
};

interface HeatmapAxes {
  xKey: string;
  yKey: string;
  valueKey: string;
}

interface HeatmapMatrix {
  xs: string[];
  ys: string[];
  values: Map<string, number>;
  min: number;
  max: number;
}

function buildMatrix(rows: Array<Record<string, unknown>>, axes: HeatmapAxes): HeatmapMatrix {
  const xs = new Set<string>();
  const ys = new Set<string>();
  const values = new Map<string, number>();
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;

  for (const row of rows) {
    const x = String(row[axes.xKey] ?? "");
    const y = String(row[axes.yKey] ?? "");
    const raw = row[axes.valueKey];
    const value = typeof raw === "number" ? raw : Number(raw);
    if (Number.isNaN(value)) continue;
    xs.add(x);
    ys.add(y);
    values.set(`${x}|${y}`, value);
    if (value < min) min = value;
    if (value > max) max = value;
  }

  return {
    xs: Array.from(xs).sort(),
    ys: Array.from(ys).sort(),
    values,
    min: Number.isFinite(min) ? min : 0,
    max: Number.isFinite(max) ? max : 0,
  };
}

function cellColor(value: number, min: number, max: number): string {
  if (max === min) return `hsl(220, 70%, ${MIN_LUMINOSITY}%)`;
  const t = (value - min) / (max - min);
  const light = MIN_LUMINOSITY + (MAX_LUMINOSITY - MIN_LUMINOSITY) * t;
  return `hsl(220, 70%, ${light}%)`;
}

function detectAxes(spec: WidgetSpec): HeatmapAxes | null {
  const { x, y, value } = spec.bindings;
  if (!x || !y || !value) return null;
  return { xKey: x, yKey: y, valueKey: value };
}

function HeatmapRenderer({ spec, rows }: RendererProps) {
  const axes = detectAxes(spec);
  if (!axes) {
    return (
      <ChartFrame spec={spec}>
        <p style={{ color: "#6b7280" }}>
          El widget no declaró bindings x/y/value para el heatmap.
        </p>
      </ChartFrame>
    );
  }

  const matrix = buildMatrix(rows, axes);
  if (matrix.xs.length === 0 || matrix.ys.length === 0) {
    return (
      <ChartFrame spec={spec}>
        <p style={{ color: "#6b7280" }}>La extracción no contiene valores numéricos válidos.</p>
      </ChartFrame>
    );
  }

  const width = AXIS_PADDING + matrix.xs.length * CELL_SIZE;
  const height = AXIS_PADDING + matrix.ys.length * CELL_SIZE + LEGEND_HEIGHT;

  return (
    <ChartFrame spec={spec}>
      <div style={{ overflow: "auto" }}>
        <svg width={width} height={height} role="img" aria-label="heatmap">
          {matrix.ys.map((yLabel, yi) => (
            <text
              key={`y-${yLabel}`}
              x={AXIS_PADDING - 8}
              y={AXIS_PADDING + yi * CELL_SIZE + CELL_SIZE / 2}
              textAnchor="end"
              dominantBaseline="middle"
              style={AXIS_LABEL_STYLE}
            >
              {yLabel}
            </text>
          ))}
          {matrix.xs.map((xLabel, xi) => (
            <text
              key={`x-${xLabel}`}
              x={AXIS_PADDING + xi * CELL_SIZE + CELL_SIZE / 2}
              y={AXIS_PADDING - 8}
              textAnchor="middle"
              style={AXIS_LABEL_STYLE}
            >
              {xLabel}
            </text>
          ))}
          {matrix.ys.flatMap((yLabel, yi) =>
            matrix.xs.map((xLabel, xi) => {
              const value = matrix.values.get(`${xLabel}|${yLabel}`);
              if (value === undefined) {
                return (
                  <rect
                    key={`${xLabel}-${yLabel}`}
                    x={AXIS_PADDING + xi * CELL_SIZE}
                    y={AXIS_PADDING + yi * CELL_SIZE}
                    width={CELL_SIZE - 2}
                    height={CELL_SIZE - 2}
                    fill="#f3f4f6"
                    stroke="#e5e7eb"
                  />
                );
              }
              return (
                <g key={`${xLabel}-${yLabel}`}>
                  <rect
                    x={AXIS_PADDING + xi * CELL_SIZE}
                    y={AXIS_PADDING + yi * CELL_SIZE}
                    width={CELL_SIZE - 2}
                    height={CELL_SIZE - 2}
                    fill={cellColor(value, matrix.min, matrix.max)}
                  />
                  <text
                    x={AXIS_PADDING + xi * CELL_SIZE + (CELL_SIZE - 2) / 2}
                    y={AXIS_PADDING + yi * CELL_SIZE + (CELL_SIZE - 2) / 2}
                    style={CELL_LABEL_STYLE}
                  >
                    {value.toLocaleString("es", { maximumFractionDigits: 1 })}
                  </text>
                </g>
              );
            }),
          )}
        </svg>
      </div>
    </ChartFrame>
  );
}

registerRenderer("heatmap", HeatmapRenderer);
