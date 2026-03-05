import type { EntryAnalysisReport, RiskLevel } from "@/lib/types";
import { Badge, Group, Paper, ScrollArea, Stack, Table, Text } from "@mantine/core";

const RISK_BADGE_COLOR: Record<RiskLevel, string> = {
  Low:      "green",
  Medium:   "yellow",
  High:     "orange",
  Critical: "red",
};

const LEVEL_COLORS: Record<string, string> = {
  DEBUG:    "#a78bfa",
  INFO:     "#60a5fa",
  WARNING:  "#fbbf24",
  ERROR:    "#f87171",
  CRITICAL: "#ef4444",
};

function tagColor(tag: string, type: "sensitive" | "sqli" | "critical"): string {
  if (type === "sqli")     return "violet";
  if (type === "critical") return "red";
  return "orange";
}

interface Props { entries: EntryAnalysisReport[] }

export default function AnomalyTable({ entries }: Props) {
  const flagged = entries.filter(
    (e) => e.is_anomaly || e.has_sensitive_data || e.has_sqli || e.has_critical_pattern
  );

  return (
    <Paper withBorder p="lg" radius="md" component="section" aria-label="Flagged entries detail">
      <Group mb="md" gap="xs">
        <Text size="xs" fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.08em" }}>
          Flagged Entries
        </Text>
        <Badge color="red" variant="light" size="sm" radius="xl" aria-label={`${flagged.length} flagged entries`}>
          {flagged.length}
        </Badge>
      </Group>

      {flagged.length === 0 ? (
        <Text c="green" size="sm">No flagged entries detected.</Text>
      ) : (
        <ScrollArea>
          <Table
            striped
            highlightOnHover
            fz="xs"
            aria-label="Entries flagged for anomalies, sensitive data, SQLi, or critical patterns"
            styles={{
              th: {
                color:         "var(--mantine-color-dimmed)",
                fontWeight:    600,
                fontSize:      "11px",
                letterSpacing: "0.05em",
                textTransform: "uppercase",
              },
              table: { minWidth: 700 },
            }}
          >
            <Table.Thead>
              <Table.Tr>
                {["#", "Level", "Source", "Score", "Flags", "Message"].map((h) => (
                  <Table.Th key={h} scope="col">{h}</Table.Th>
                ))}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {flagged.map((e) => {
                const lvlColor = LEVEL_COLORS[e.level.toUpperCase()] ?? "#94a3b8";
                return (
                  <Table.Tr key={e.id}>
                    <Table.Td c="dimmed">{entries.indexOf(e)}</Table.Td>
                    <Table.Td>
                      <Text fw={600} size="xs" style={{ color: lvlColor }}>{e.level}</Text>
                    </Table.Td>
                    <Table.Td c="dimmed">{e.source}</Table.Td>
                    <Table.Td>
                      <Badge color={RISK_BADGE_COLOR[e.risk_level as RiskLevel] ?? "gray"} variant="light" size="xs" radius="sm">
                        {e.risk_score.toFixed(1)}
                      </Badge>
                    </Table.Td>
                    <Table.Td style={{ minWidth: 180 }}>
                      <Stack gap={2}>
                        {e.is_anomaly && (
                          <Badge color="red" variant="light" size="xs" radius="sm">anomaly</Badge>
                        )}
                        {e.has_sensitive_data && e.sensitive_data_tags.map((t) => (
                          <Badge key={t} color={tagColor(t, "sensitive")} variant="light" size="xs" radius="sm">{t}</Badge>
                        ))}
                        {e.has_sqli && e.sqli_tags.map((t) => (
                          <Badge key={t} color={tagColor(t, "sqli")} variant="light" size="xs" radius="sm">{t}</Badge>
                        ))}
                        {e.has_critical_pattern && e.critical_pattern_tags.map((t) => (
                          <Badge key={t} color={tagColor(t, "critical")} variant="light" size="xs" radius="sm">{t}</Badge>
                        ))}
                      </Stack>
                    </Table.Td>
                    <Table.Td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={e.message}>
                      {e.message}
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </ScrollArea>
      )}
    </Paper>
  );
}
