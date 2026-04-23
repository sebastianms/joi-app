// Area chart renderer (T128).
// Same input shape as line_chart but with filled area beneath. Useful for
// cumulative trends (the LLM picks this variant when the user asks for
// "acumulado" / "evolución").

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { registerRenderer, type RendererProps } from "../registry";
import { CHART_COLORS, ChartFrame } from "./_chart-frame";

function AreaChartRenderer({ spec, rows }: RendererProps) {
  const { x, y } = spec.bindings;
  if (!x || !y) {
    return (
      <ChartFrame spec={spec}>
        <p style={{ color: "#6b7280" }}>
          El widget no declaró bindings x/y para el área.
        </p>
      </ChartFrame>
    );
  }

  const { x_label, y_label } = spec.visual_options ?? {};
  const fillColor = CHART_COLORS[0];

  return (
    <ChartFrame spec={spec}>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={rows} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
          <defs>
            <linearGradient id="area-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={fillColor} stopOpacity={0.6} />
              <stop offset="100%" stopColor={fillColor} stopOpacity={0.05} />
            </linearGradient>
          </defs>
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
          <Tooltip />
          <Legend />
          <Area
            type="monotone"
            dataKey={y}
            stroke={fillColor}
            strokeWidth={2}
            fill="url(#area-gradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

registerRenderer("area_chart", AreaChartRenderer);
