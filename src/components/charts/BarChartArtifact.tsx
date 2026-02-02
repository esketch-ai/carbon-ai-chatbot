"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface BarChartData {
  name: string;
  value: number;
  [key: string]: string | number;
}

interface BarChartArtifactProps {
  data: BarChartData[];
  title?: string;
  xAxisKey?: string;
  yAxisKey?: string;
  valueFormatter?: (value: number) => string;
  colors?: string[];
}

const DEFAULT_COLORS = [
  "#3b82f6", // blue
  "#10b981", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // purple
  "#ec4899", // pink
];

export function BarChartArtifact({
  data,
  title,
  xAxisKey = "name",
  yAxisKey = "value",
  valueFormatter,
  colors = DEFAULT_COLORS,
}: BarChartArtifactProps) {
  return (
    <div className="w-full h-full flex flex-col p-6 bg-white dark:bg-zinc-900">
      {title && (
        <h3 className="text-lg font-semibold mb-4 text-foreground">
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey={xAxisKey}
            className="text-sm"
            tick={{ fill: "currentColor" }}
          />
          <YAxis
            className="text-sm"
            tick={{ fill: "currentColor" }}
            tickFormatter={valueFormatter}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--background)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
            }}
            formatter={valueFormatter}
          />
          <Legend />
          <Bar dataKey={yAxisKey} radius={[8, 8, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={colors[index % colors.length]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
