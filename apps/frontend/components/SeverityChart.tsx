"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import type { EntryAnalysisReport } from "@/lib/types";
import { Paper, Text } from "@mantine/core";

const LEVEL_COLORS: Record<string, string> = {
  DEBUG:    "#a78bfa",
  INFO:     "#60a5fa",
  WARNING:  "#fbbf24",
  ERROR:    "#f87171",
  CRITICAL: "#ef4444",
};

const ORDER = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

interface Props { entries: EntryAnalysisReport[] }

export default function SeverityChart({ entries }: Props) {
  const counts: Record<string, number> = {};
  for (const e of entries) {
    const lvl = e.level.toUpperCase() === "WARN" ? "WARNING" : e.level.toUpperCase();
    counts[lvl] = (counts[lvl] ?? 0) + 1;
  }

  const data = [
    ...ORDER.filter((l) => counts[l] !== undefined).map((l) => ({ level: l, count: counts[l] })),
    ...Object.entries(counts).filter(([l]) => !ORDER.includes(l)).map(([l, c]) => ({ level: l, count: c })),
  ];

  return (
    <Paper withBorder p="lg" radius="md" h="100%" component="section" aria-label="Severity distribution chart">
      <Text size="xs" fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.08em" }} mb="md">
        Severity Distribution
      </Text>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} barCategoryGap="30%">
          <XAxis
            dataKey="level"
            tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "inherit" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "inherit" }}
            axisLine={false}
            tickLine={false}
            width={28}
            allowDecimals={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            contentStyle={{
              background: "#0f1729", border: "1px solid #1e293b",
              borderRadius: "8px", color: "#e2e8f0",
              fontFamily: "inherit", fontSize: "12px",
            }}
            labelStyle={{ color: "#94a3b8" }}
            itemStyle={{ color: "#e2e8f0" }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.level} fill={LEVEL_COLORS[entry.level] ?? "#64748b"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Paper>
  );
}
