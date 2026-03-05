"use client";

import { useState, useCallback } from "react";
import { notifications } from "@mantine/notifications";
import { nprogress } from "@mantine/nprogress";
import {
  Alert, Badge, Button, Container, Grid, Group, Paper,
  SimpleGrid, Skeleton, Stack, Text,
} from "@mantine/core";
import { useUser, useAuth } from "@clerk/nextjs";
import { analyzeForensic, RateLimitError } from "@/lib/api";
import type { ForensicAnalysisReport, LogEntry, RiskLevel } from "@/lib/types";
import LogInput from "@/components/LogInput";
import RiskGauge from "@/components/RiskGauge";
import SeverityChart from "@/components/SeverityChart";
import EntropyTimeline from "@/components/EntropyTimeline";
import AnomalyTable from "@/components/AnomalyTable";
import SkeletonDashboard from "@/components/SkeletonDashboard";
import TopFlagged from "@/components/TopFlagged";
import RiskHistogram from "@/components/RiskHistogram";
import SourceBreakdown from "@/components/SourceBreakdown";
import TagFrequency from "@/components/TagFrequency";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const RISK_COLORS: Record<RiskLevel, string> = {
  Low:      "#22c55e",
  Medium:   "#f59e0b",
  High:     "#f97316",
  Critical: "#ef4444",
};

function downloadJson(report: ForensicAnalysisReport) {
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `lognis-report-${report.analyzed_at.replace(/[:.]/g, "-")}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadCsv(report: ForensicAnalysisReport) {
  const header =
    "id,source,level,message,entropy,is_anomaly,risk_score,risk_level,has_sensitive_data,has_sqli,has_critical_pattern";
  const rows = report.entries.map((e) =>
    [
      e.id,
      JSON.stringify(e.source),
      e.level,
      JSON.stringify(e.message),
      e.entropy,
      e.is_anomaly,
      e.risk_score,
      e.risk_level,
      e.has_sensitive_data,
      e.has_sqli,
      e.has_critical_pattern,
    ].join(",")
  );
  const csv  = [header, ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `lognis-report-${report.analyzed_at.replace(/[:.]/g, "-")}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── StatCard ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <Paper withBorder p="md" radius="md" h="100%">
      <Stack gap={4} justify="center" h="100%">
        <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: "0.05em" }}>
          {label}
        </Text>
        <Text fw={800} size="xl" style={{ color: accent ?? "var(--mantine-color-white)", lineHeight: 1 }}>
          {value}
        </Text>
      </Stack>
    </Paper>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const { isLoaded, user } = useUser();
  const { getToken }       = useAuth();
  const [loading, setLoading] = useState(false);
  const [report,  setReport ] = useState<ForensicAnalysisReport | null>(null);

  const handleAnalyze = useCallback(
    async (entries: LogEntry[]) => {
      setLoading(true);
      setReport(null);
      nprogress.start();
      try {
        const userId = user?.id;
        const token  = userId ? (await getToken()) ?? undefined : undefined;
        const result = await analyzeForensic(entries, userId, token);
        setReport(result);
        notifications.show({
          title:   "Analysis complete",
          message: `${result.total_entries} entries — risk: ${result.overall_risk_level}`,
          color:   "green",
        });
      } catch (e) {
        if (e instanceof RateLimitError) {
          notifications.show({
            title:   "Rate limit reached",
            message: "Sign in for higher limits or wait a moment.",
            color:   "orange",
          });
        } else {
          const msg = e instanceof Error ? e.message : "Unknown error";
          notifications.show({
            title:   "Analysis failed",
            message: msg,
            color:   "red",
          });
        }
      } finally {
        setLoading(false);
        nprogress.complete();
      }
    },
    [user, getToken]
  );

  return (
    <main id="main">
      <Container size="xl" px={{ base: "md", md: "xl" }} py="xl" maw={1600}>
        <Stack gap="xl">

          {/* Guest CTA */}
          {isLoaded && !user && (
            <Alert
              color="blue"
              variant="light"
              radius="md"
              icon={
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              }
            >
              Sign in to save your analysis history and access past reports.
            </Alert>
          )}

          {/* Input */}
          <LogInput onSubmit={handleAnalyze} loading={loading} />

          {/* Results region */}
          <div aria-live="polite" aria-atomic="false">
            {loading && <SkeletonDashboard />}

            {!loading && report && (
              <Stack gap="lg">

                {/* Row 1: Gauge + 6 stat cards */}
                <Grid gutter="md" align="stretch">
                  <Grid.Col span="content">
                    <RiskGauge score={report.overall_risk_score} level={report.overall_risk_level} />
                  </Grid.Col>
                  <Grid.Col span="auto">
                    <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="sm" h="100%">
                      <StatCard label="Total Entries"    value={report.total_entries} />
                      <StatCard label="Anomalies"        value={report.anomaly_count}           accent={report.anomaly_count > 0           ? "#f87171" : undefined} />
                      <StatCard label="Mean Entropy"     value={report.mean_entropy.toFixed(3)} accent="#60a5fa" />
                      <StatCard label="Sensitive Data"   value={report.sensitive_entry_count}   accent={report.sensitive_entry_count > 0   ? "#f97316" : undefined} />
                      <StatCard label="SQLi Detected"    value={report.sqli_entry_count}        accent={report.sqli_entry_count > 0        ? "#a855f7" : undefined} />
                      <StatCard label="Critical Patterns" value={report.critical_pattern_count} accent={report.critical_pattern_count > 0 ? "#ef4444" : undefined} />
                    </SimpleGrid>
                  </Grid.Col>
                </Grid>

                {/* Row 2: Risk breakdown */}
                <Paper withBorder p="lg" radius="md">
                  <SimpleGrid cols={{ base: 2, sm: 4 }}>
                    {[
                      { label: "Entropy Factor",   val: report.overall_risk_breakdown.entropy_factor.toFixed(3)   },
                      { label: "Anomaly Factor",   val: report.overall_risk_breakdown.anomaly_factor.toFixed(3)   },
                      { label: "Heuristic Penalty", val: report.overall_risk_breakdown.heuristic_penalty.toFixed(3) },
                      { label: "Raw Total",         val: report.overall_risk_breakdown.raw_total.toFixed(3), accent: RISK_COLORS[report.overall_risk_level] },
                    ].map(({ label, val, accent }) => (
                      <div key={label}>
                        <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: "0.05em" }} mb={4}>
                          {label}
                        </Text>
                        <Text fw={700} size="lg" style={{ color: accent ?? "var(--mantine-color-white)" }}>
                          {val}
                        </Text>
                      </div>
                    ))}
                  </SimpleGrid>
                </Paper>

                {/* Row 3: Top Flagged */}
                <TopFlagged entries={report.entries} />

                {/* Row 4: Severity + Entropy */}
                <Grid gutter="lg" align="stretch">
                  <Grid.Col span={{ base: 12, md: 6 }}><SeverityChart entries={report.entries} /></Grid.Col>
                  <Grid.Col span={{ base: 12, md: 6 }}><EntropyTimeline entries={report.entries} meanEntropy={report.mean_entropy} /></Grid.Col>
                </Grid>

                {/* Row 5: Histogram + Source */}
                <Grid gutter="lg" align="stretch">
                  <Grid.Col span={{ base: 12, md: 6 }}><RiskHistogram entries={report.entries} /></Grid.Col>
                  <Grid.Col span={{ base: 12, md: 6 }}><SourceBreakdown entries={report.entries} /></Grid.Col>
                </Grid>

                {/* Row 6: Tag frequency */}
                <TagFrequency entries={report.entries} />

                {/* Row 7: Anomaly table */}
                <AnomalyTable entries={report.entries} />

                {/* Row 8: Export + timestamp */}
                <Group justify="space-between" wrap="wrap" gap="sm">
                  <Group gap="xs">
                    <Button variant="light" color="lognis" size="sm" onClick={() => downloadJson(report)}>
                      Export JSON
                    </Button>
                    <Button variant="light" color="lognis" size="sm" onClick={() => downloadCsv(report)}>
                      Export CSV
                    </Button>
                  </Group>
                  <Text size="xs" c="dimmed">
                    Analyzed at {new Date(report.analyzed_at).toLocaleString()}
                  </Text>
                </Group>

              </Stack>
            )}
          </div>

        </Stack>
      </Container>
    </main>
  );
}
