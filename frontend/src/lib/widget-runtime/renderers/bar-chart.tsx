// Bar chart renderer (T122).
// Uses bindings.x as the category axis, bindings.y as the numeric series.
// Emits a widget:error-equivalent fallback (empty state) when bindings are
// missing rather than crashing the runtime.

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { registerRenderer, type RendererProps } from "../registry";
import { CHART_COLORS, ChartFrame } from "./_chart-frame";

function BarChartRenderer({ spec, rows }: RendererProps) {
  const { x, y } = spec.bindings;
  if (!x || !y) {
    return (
      <ChartFrame spec={spec}>
        <p style={{ color: "#6b7280" }}>
          El widget no declaró bindings x/y para el eje categórico y la serie numérica.
        </p>
      </ChartFrame>
    );
  }

  const { x_label, y_label } = spec.visual_options ?? {};

  return (
    <ChartFrame spec={spec}>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey={x}
            label={x_label ? { value: x_label, position: "insideBottom", offset: -16 } : undefined}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            label={y_label ? { value: y_label, angle: -90, position: "insideLeft" } : undefined}
            tick={{ fontSize: 12 }}
          />
          <Tooltip cursor={{ fill: "rgba(37, 99, 235, 0.08)" }} />
          <Bar dataKey={y} fill={CHART_COLORS[0]} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

registerRenderer("bar_chart", BarChartRenderer);
