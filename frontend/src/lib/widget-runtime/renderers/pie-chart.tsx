// Pie chart renderer (T124).
// bindings.label → category slice, bindings.value → numeric magnitude.
// Applicability validator already rejects negatives and cardinality > 10.

import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { registerRenderer, type RendererProps } from "../registry";
import { CHART_COLORS, ChartFrame } from "./_chart-frame";

function PieChartRenderer({ spec, rows }: RendererProps) {
  const { label, value } = spec.bindings;
  if (!label || !value) {
    return (
      <ChartFrame spec={spec}>
        <p style={{ color: "#6b7280" }}>
          El widget no declaró bindings label/value para el pastel.
        </p>
      </ChartFrame>
    );
  }

  return (
    <ChartFrame spec={spec}>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={rows}
            dataKey={value}
            nameKey={label}
            outerRadius={100}
            innerRadius={0}
            paddingAngle={1}
          >
            {rows.map((_, idx) => (
              <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

registerRenderer("pie_chart", PieChartRenderer);
