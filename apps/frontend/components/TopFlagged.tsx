import type { EntryAnalysisReport, RiskLevel } from "@/lib/types";
import { Badge, Card, Group, SimpleGrid, Stack, Text } from "@mantine/core";

const RISK_BADGE_COLOR: Record<RiskLevel, string> = {
  Low:      "green",
  Medium:   "yellow",
  High:     "orange",
  Critical: "red",
};

const RISK_CARD_STYLE: Record<RiskLevel, React.CSSProperties> = {
  Low:      { borderColor: "rgba(34,197,94,0.3)",  background: "rgba(34,197,94,0.05)"  },
  Medium:   { borderColor: "rgba(245,158,11,0.3)", background: "rgba(245,158,11,0.05)" },
  High:     { borderColor: "rgba(249,115,22,0.3)", background: "rgba(249,115,22,0.05)" },
  Critical: { borderColor: "rgba(239,68,68,0.3)",  background: "rgba(239,68,68,0.05)"  },
};

function tagBadgeColor(tag: string): string {
  if (tag.includes("sqli") || tag.includes("sql")) return "violet";
  if (tag.includes("critical"))                    return "red";
  return "orange";
}

export default function TopFlagged({ entries }: { entries: EntryAnalysisReport[] }) {
  const top = [...entries].sort((a, b) => b.risk_score - a.risk_score).slice(0, 3);
  if (top.length === 0) return null;

  const allTags = (e: EntryAnalysisReport) => [
    ...e.sensitive_data_tags.map((t) => ({ label: t, type: "sensitive" as const })),
    ...e.sqli_tags.map((t)            => ({ label: t, type: "sqli"      as const })),
    ...e.critical_pattern_tags.map((t) => ({ label: t, type: "critical" as const })),
  ];

  return (
    <section aria-label="Top flagged entries">
      <Text size="xs" fw={600} tt="uppercase" c="dimmed" style={{ letterSpacing: "0.08em" }} mb="sm">
        Top Flagged
      </Text>
      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
        {top.map((entry, i) => {
          const tags = allTags(entry);
          return (
            <Card
              key={entry.id}
              withBorder
              radius="md"
              p="md"
              style={RISK_CARD_STYLE[entry.risk_level]}
            >
              <Stack gap="xs">
                {/* Rank + risk badge */}
                <Group justify="space-between" gap="xs">
                  <Text size="xs" c="dimmed" ff="monospace">#{i + 1}</Text>
                  <Badge
                    color={RISK_BADGE_COLOR[entry.risk_level]}
                    variant="light"
                    size="sm"
                    radius="xl"
                  >
                    {entry.risk_level} {entry.risk_score.toFixed(2)}
                  </Badge>
                </Group>

                {/* Source + level */}
                <Group gap={6}>
                  <Text size="xs" c="dimmed" ff="monospace" style={{ maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={entry.source}>
                    {entry.source}
                  </Text>
                  <Text size="xs" c="dimmed">·</Text>
                  <Text size="xs" c="dimmed">{entry.level}</Text>
                </Group>

                {/* Message */}
                <Text size="sm" lineClamp={2}>{entry.message}</Text>

                {/* Tags */}
                {tags.length > 0 && (
                  <Group gap={4} wrap="wrap">
                    {tags.map((tag, ti) => (
                      <Badge
                        key={ti}
                        color={tagBadgeColor(tag.label)}
                        variant="light"
                        size="xs"
                        radius="sm"
                      >
                        {tag.label}
                      </Badge>
                    ))}
                  </Group>
                )}
              </Stack>
            </Card>
          );
        })}
      </SimpleGrid>
    </section>
  );
}
