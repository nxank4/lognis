import type { EntryAnalysisReport } from "@/lib/types";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
} from "recharts";
import { Paper, Text } from "@mantine/core";

const BANDS = [
  { label: "0–2",  min: 0, max: 2,      color: "#22c55e" },
  { label: "2–4",  min: 2, max: 4,      color: "#84cc16" },
  { label: "4–6",  min: 4, max: 6,      color: "#f59e0b" },
  { label: "6–8",  min: 6, max: 8,      color: "#f97316" },
  { label: "8–10", min: 8, max: 10.001, color: "#ef4444" },
];

export default function RiskHistogram({ entries }: { entries: EntryAnalysisReport[] }) {
  const data = BANDS.map((band) => ({
    label: band.label,
    count: entries.filter((e) => e.risk_score >= band.min && e.risk_score < band.max).length,
    color: band.color,
  }));

  return (
    <Paper withBorder p="lg" radius="md" h="100%" component="section" aria-label="Risk score histogram">
      <Text size="xs" fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.08em" }} mb="md">
        Risk Distribution
      </Text>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <XAxis
            dataKey="label"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              background: "#0f172a", border: "1px solid #1e293b",
              borderRadius: "8px", color: "#f1f5f9", fontSize: "12px",
            }}
            labelStyle={{ color: "#94a3b8" }}
            itemStyle={{ color: "#f1f5f9" }}
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            formatter={(value: number) => [value, "Entries"]}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((d, i) => <Cell key={i} fill={d.color} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Paper>
  );
}
