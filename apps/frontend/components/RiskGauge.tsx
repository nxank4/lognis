"use client";

import { PieChart, Pie, Cell } from "recharts";
import type { RiskLevel } from "@/lib/types";
import { Badge, Paper, Stack, Text } from "@mantine/core";

const HEX_COLORS: Record<RiskLevel, string> = {
  Low:      "#22c55e",
  Medium:   "#f59e0b",
  High:     "#f97316",
  Critical: "#ef4444",
};

const BADGE_COLOR: Record<RiskLevel, string> = {
  Low:      "green",
  Medium:   "yellow",
  High:     "orange",
  Critical: "red",
};

const TRACK_COLOR = "#1e293b";

interface Props { score: number; level: RiskLevel }

export default function RiskGauge({ score, level }: Props) {
  const color = HEX_COLORS[level];
  const data  = [
    { name: "Risk",      value: parseFloat(score.toFixed(2)) },
    { name: "Remaining", value: parseFloat((10 - score).toFixed(2)) },
  ];

  return (
    <Paper
      withBorder
      p="lg"
      radius="md"
      h="100%"
      component="section"
      aria-label={`Overall risk score: ${score.toFixed(1)} out of 10, level: ${level}`}
      style={{ minWidth: 200 }}
    >
      <Stack align="center" gap="xs">
        <Text size="xs" fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.08em" }}>
          Overall Risk Score
        </Text>

        <div className="relative" style={{ width: 160, height: 160 }}>
          <PieChart width={160} height={160}>
            <Pie
              data={data}
              cx={75}
              cy={75}
              innerRadius={52}
              outerRadius={72}
              startAngle={90}
              endAngle={-270}
              dataKey="value"
              strokeWidth={0}
              isAnimationActive
            >
              <Cell key="risk"      fill={color}       />
              <Cell key="remaining" fill={TRACK_COLOR} />
            </Pie>
          </PieChart>

          {/* Center overlay */}
          <div
            style={{
              position: "absolute", inset: 0,
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              pointerEvents: "none",
            }}
            aria-hidden="true"
          >
            <span style={{ fontSize: 32, fontWeight: 800, lineHeight: 1, color }}>
              {score.toFixed(1)}
            </span>
            <Text size="xs" c="dimmed" mt={2}>/ 10</Text>
          </div>
        </div>

        <Badge
          color={BADGE_COLOR[level]}
          variant="light"
          size="sm"
          radius="xl"
          style={{ letterSpacing: "0.08em" }}
        >
          {level.toUpperCase()}
        </Badge>
      </Stack>
    </Paper>
  );
}
