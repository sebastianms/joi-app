// Line chart renderer (T123).
// Uses bindings.x as the ordered axis (datetime or ordinal) and bindings.y
// as the numeric series. Optional bindings.series splits into multiple
// lines grouped by the series column's value.

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { registerRenderer, type RendererProps } from "../registry";
import { CHART_COLORS, ChartFrame } from "./_chart-frame";

interface PivotKeys {
  x: string;
  y: string;
  series: string;
}

function pivotBySeries(
  rows: Array<Record<string, unknown>>,
  keys: PivotKeys,
): { data: Array<Record<string, unknown>>; seriesKeys: string[] } {
  const byX = new Map<unknown, Record<string, unknown>>();
  const seen = new Set<string>();
  for (const row of rows) {
    const xValue = row[keys.x];
    const seriesValue = String(row[keys.series] ?? "");
    seen.add(seriesValue);
    const bucket = byX.get(xValue) ?? { [keys.x]: xValue };
    bucket[seriesValue] = row[keys.y];
    byX.set(xValue, bucket);
  }
  return { data: Array.from(byX.values()), seriesKeys: Array.from(seen) };
}

function LineChartRenderer({ spec, rows }: RendererProps) {
  const { x, y, series } = spec.bindings;
  if (!x || !y) {
    return (
      <ChartFrame spec={spec}>
        <p style={{ color: "#6b7280" }}>
          El widget no declaró bindings x/y para la serie temporal.
        </p>
      </ChartFrame>
    );
  }

  const { x_label, y_label } = spec.visual_options ?? {};

  const chartData = series ? pivotBySeries(rows, { x, y, series }) : null;
  const data = chartData ? chartData.data : rows;

  return (
    <ChartFrame spec={spec}>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
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
          {chartData ? (
            <>
              <Legend />
              {chartData.seriesKeys.map((key, idx) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={CHART_COLORS[idx % CHART_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </>
          ) : (
            <Line
              type="monotone"
              dataKey={y}
              stroke={CHART_COLORS[0]}
              strokeWidth={2}
              dot={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

registerRenderer("line_chart", LineChartRenderer);
