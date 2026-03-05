import type { EntryAnalysisReport } from "@/lib/types";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
} from "recharts";
import { Paper, Text } from "@mantine/core";

function riskColor(score: number): string {
  if (score >= 8) return "#ef4444";
  if (score >= 6) return "#f97316";
  if (score >= 4) return "#f59e0b";
  return "#22c55e";
}

export default function SourceBreakdown({ entries }: { entries: EntryAnalysisReport[] }) {
  const map: Record<string, { total: number; count: number }> = {};
  for (const e of entries) {
    if (!map[e.source]) map[e.source] = { total: 0, count: 0 };
    map[e.source].total += e.risk_score;
    map[e.source].count += 1;
  }

  const data = Object.entries(map)
    .map(([source, { total, count }]) => ({ source, avg: total / count }))
    .sort((a, b) => b.avg - a.avg)
    .slice(0, 12);

  if (data.length === 0) return null;

  const chartHeight = 220;

  return (
    <Paper withBorder p="lg" radius="md" h="100%" component="section" aria-label="Source risk breakdown">
      <Text size="xs" fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.08em" }} mb="md">
        Avg Risk by Source
      </Text>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart layout="vertical" data={data} margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
          <XAxis
            type="number"
            domain={[0, 10]}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="source"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={90}
          />
          <Tooltip
            contentStyle={{
              background: "#0f172a", border: "1px solid #1e293b",
              borderRadius: "8px", color: "#f1f5f9", fontSize: "12px",
            }}
            labelStyle={{ color: "#94a3b8" }}
            itemStyle={{ color: "#f1f5f9" }}
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            formatter={(value: number) => [value.toFixed(3), "Avg Risk"]}
          />
          <Bar dataKey="avg" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => <Cell key={i} fill={riskColor(d.avg)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Paper>
  );
}
