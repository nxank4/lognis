"use client";

import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import type { EntryAnalysisReport } from "@/lib/types";
import { Group, Paper, Text } from "@mantine/core";

interface Props {
  entries:     EntryAnalysisReport[];
  meanEntropy: number;
}

export default function EntropyTimeline({ entries, meanEntropy }: Props) {
  const data = entries.map((e, i) => ({
    idx:     i,
    entropy: parseFloat(e.entropy.toFixed(3)),
    anomaly: e.is_anomaly,
  }));

  return (
    <Paper withBorder p="lg" radius="md" h="100%" component="section" aria-label="Entropy timeline chart">
      <Group justify="space-between" mb="md">
        <Text size="xs" fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.08em" }}>
          Entropy Timeline
        </Text>
        <Text size="xs" c="blue.4" aria-label={`Mean entropy: ${meanEntropy.toFixed(3)}`}>
          mean: {meanEntropy.toFixed(3)}
        </Text>
      </Group>

      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <XAxis
            dataKey="idx"
            tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "inherit" }}
            axisLine={false}
            tickLine={false}
            label={{ value: "entry index", position: "insideBottomRight", offset: -4, fill: "#64748b", fontSize: 10 }}
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "inherit" }}
            axisLine={false}
            tickLine={false}
            width={36}
            domain={["auto", "auto"]}
          />
          <Tooltip
            cursor={{ stroke: "#475569" }}
            contentStyle={{
              background: "#0f1729", border: "1px solid #1e293b",
              borderRadius: "8px", color: "#e2e8f0",
              fontFamily: "inherit", fontSize: "12px",
            }}
            labelStyle={{ color: "#94a3b8" }}
            itemStyle={{ color: "#e2e8f0" }}
            formatter={(val: number) => [val.toFixed(3), "entropy"]}
            labelFormatter={(i: number) => `Entry #${i}`}
          />
          <ReferenceLine
            y={meanEntropy}
            stroke="#3b82f6"
            strokeDasharray="4 4"
            strokeOpacity={0.5}
            label={{ value: "mean", fill: "#3b82f6", fontSize: 10, position: "insideTopRight" }}
          />
          <Line
            type="monotone"
            dataKey="entropy"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={(props) => {
              const { cx, cy, payload } = props;
              if (payload.anomaly) {
                return (
                  <circle
                    key={`dot-${payload.idx}`}
                    cx={cx} cy={cy} r={5}
                    fill="#f87171" stroke="#0f1729" strokeWidth={1.5}
                  />
                );
              }
              return (
                <circle
                  key={`dot-${payload.idx}`}
                  cx={cx} cy={cy} r={3}
                  fill="#60a5fa" stroke="none"
                />
              );
            }}
            activeDot={{ r: 5, fill: "#93c5fd" }}
          />
        </LineChart>
      </ResponsiveContainer>

      <Text size="xs" c="dimmed" mt="xs">
        <span
          style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: "#f87171", marginRight: 6, flexShrink: 0 }}
          aria-hidden="true"
        />
        Red dots = anomalies (Z-score outliers)
      </Text>
    </Paper>
  );
}
