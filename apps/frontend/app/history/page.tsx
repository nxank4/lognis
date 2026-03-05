"use client";

import { useEffect, useState } from "react";
import { useUser, useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { nprogress } from "@mantine/nprogress";
import { getHistory } from "@/lib/api";
import type { AnalysisResultSummary, RiskLevel } from "@/lib/types";
import {
  Alert, Badge, Center, Container, Loader, ScrollArea, Stack, Table, Text, Title,
} from "@mantine/core";

const RISK_BADGE_COLOR: Record<RiskLevel, string> = {
  Low:      "green",
  Medium:   "yellow",
  High:     "orange",
  Critical: "red",
};

const COLUMNS = [
  "Date", "Entries", "Risk", "Score",
  "Anomalies", "Sensitive", "SQLi", "Critical", "Mean Entropy",
];

export default function HistoryPage() {
  const { isLoaded, user } = useUser();
  const { getToken }       = useAuth();
  const router             = useRouter();
  const [rows,     setRows]     = useState<AnalysisResultSummary[]>([]);
  const [fetching, setFetching] = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    if (!user) {
      router.replace("/");
      return;
    }
    setFetching(true);
    nprogress.start();
    getToken()
      .then((token) => getHistory(user.id, token ?? undefined))
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load history"))
      .finally(() => {
        setFetching(false);
        nprogress.complete();
      });
  }, [isLoaded, user, router, getToken]);

  return (
    <main id="main">
      <Container size="xl" px={{ base: "md", md: "xl" }} py="xl" maw={1600}>
        <Stack gap="xl">

          {/* Page heading */}
          <div>
            <Title order={1} size="h2" mb={6}>Analysis History</Title>
            <Text c="dimmed" size="sm">Your 50 most recent forensic reports.</Text>
          </div>

          {/* Loading */}
          {fetching && (
            <Center py="xl">
              <Loader color="lognis" size="sm" />
            </Center>
          )}

          {/* Error */}
          {error && !fetching && (
            <Alert color="red" variant="light" radius="md" role="alert">
              {error}
            </Alert>
          )}

          {/* Empty state */}
          {!fetching && !error && rows.length === 0 && (
            <Center
              py="xl"
              style={{
                border:       "1px dashed var(--mantine-color-default-border)",
                borderRadius: "var(--mantine-radius-md)",
              }}
            >
              <Text c="dimmed" size="sm">
                No analysis history yet. Run your first forensic report from the home page.
              </Text>
            </Center>
          )}

          {/* Table */}
          {!fetching && rows.length > 0 && (
            <ScrollArea>
              <Table
                striped
                highlightOnHover
                withTableBorder
                fz="xs"
                styles={{
                  thead: { background: "#0a0f1e" },
                  th: {
                    color:         "var(--mantine-color-dimmed)",
                    fontWeight:    600,
                    fontSize:      "11px",
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                    whiteSpace:    "nowrap",
                  },
                  table: { minWidth: 700 },
                }}
              >
                <Table.Thead>
                  <Table.Tr>
                    {COLUMNS.map((h) => <Table.Th key={h} scope="col">{h}</Table.Th>)}
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {rows.map((row) => (
                    <Table.Tr key={row.id}>
                      <Table.Td style={{ whiteSpace: "nowrap" }}>
                        {new Date(row.analyzed_at).toLocaleString()}
                      </Table.Td>
                      <Table.Td>{row.total_entries}</Table.Td>
                      <Table.Td>
                        <Badge
                          color={RISK_BADGE_COLOR[row.overall_risk_level]}
                          variant="light"
                          size="sm"
                          radius="sm"
                        >
                          {row.overall_risk_level}
                        </Badge>
                      </Table.Td>
                      <Table.Td>{row.overall_risk_score.toFixed(3)}</Table.Td>
                      <Table.Td>
                        <Text size="xs" c={row.anomaly_count > 0 ? "red.4" : undefined}>
                          {row.anomaly_count}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c={row.sensitive_entry_count > 0 ? "orange.4" : undefined}>
                          {row.sensitive_entry_count}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c={row.sqli_entry_count > 0 ? "violet.4" : undefined}>
                          {row.sqli_entry_count}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c={row.critical_pattern_count > 0 ? "red.4" : undefined}>
                          {row.critical_pattern_count}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="blue.4">{row.mean_entropy.toFixed(3)}</Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          )}

        </Stack>
      </Container>
    </main>
  );
}
