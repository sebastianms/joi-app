// Scatter plot renderer (T126).
// bindings.x and bindings.y are both numeric. Applicability caps at 2000 points.

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { registerRenderer, type RendererProps } from "../registry";
import { CHART_COLORS, ChartFrame } from "./_chart-frame";

function ScatterRenderer({ spec, rows }: RendererProps) {
  const { x, y } = spec.bindings;
  if (!x || !y) {
    return (
      <ChartFrame spec={spec}>
        <p style={{ color: "#6b7280" }}>
          El widget no declaró bindings x/y para el scatter.
        </p>
      </ChartFrame>
    );
  }

  const { x_label, y_label } = spec.visual_options ?? {};

  return (
    <ChartFrame spec={spec}>
      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            type="number"
            dataKey={x}
            name={x_label ?? x}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            type="number"
            dataKey={y}
            name={y_label ?? y}
            tick={{ fontSize: 12 }}
          />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={rows} fill={CHART_COLORS[0]} />
        </ScatterChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

registerRenderer("scatter_plot", ScatterRenderer);
