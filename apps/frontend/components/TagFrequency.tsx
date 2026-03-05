import type { EntryAnalysisReport } from "@/lib/types";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
} from "recharts";
import { Paper, Text } from "@mantine/core";

function tagColor(tag: string): string {
  if (tag.includes("sqli") || tag.includes("sql")) return "#a855f7";
  if (tag.includes("critical"))                    return "#ef4444";
  return "#f97316";
}

export default function TagFrequency({ entries }: { entries: EntryAnalysisReport[] }) {
  const freq: Record<string, number> = {};
  for (const e of entries) {
    for (const t of e.sensitive_data_tags)    freq[t] = (freq[t] ?? 0) + 1;
    for (const t of e.sqli_tags)              freq[t] = (freq[t] ?? 0) + 1;
    for (const t of e.critical_pattern_tags)  freq[t] = (freq[t] ?? 0) + 1;
  }

  const data = Object.entries(freq)
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count);

  if (data.length === 0) return null;

  const chartHeight = Math.max(100, data.length * 28 + 20);

  return (
    <Paper withBorder p="lg" radius="md" component="section" aria-label="Tag frequency chart">
      <Text size="xs" fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.08em" }} mb="md">
        Tag Frequency
      </Text>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart layout="vertical" data={data} margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
          <XAxis
            type="number"
            allowDecimals={false}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="tag"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={110}
          />
          <Tooltip
            contentStyle={{
              background: "#0f172a", border: "1px solid #1e293b",
              borderRadius: "8px", color: "#f1f5f9", fontSize: "12px",
            }}
            labelStyle={{ color: "#94a3b8" }}
            itemStyle={{ color: "#f1f5f9" }}
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            formatter={(value: number) => [value, "Occurrences"]}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => <Cell key={i} fill={tagColor(d.tag)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Paper>
  );
}
