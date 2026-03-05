import { Grid, SimpleGrid, Skeleton, Stack } from "@mantine/core";

export default function SkeletonDashboard() {
  return (
    <Stack gap="lg" role="status" aria-label="Loading analysis results">
      {/* Gauge + 6 stat cards */}
      <Grid gutter="md" align="stretch">
        <Grid.Col span="content">
          <Skeleton height={220} width={200} radius="md" />
        </Grid.Col>
        <Grid.Col span="auto">
          <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="sm">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} height={100} radius="md" />
            ))}
          </SimpleGrid>
        </Grid.Col>
      </Grid>

      {/* Risk breakdown */}
      <Skeleton height={80} radius="md" />

      {/* Top flagged (3 cards) */}
      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} height={140} radius="md" />
        ))}
      </SimpleGrid>

      {/* Charts row 1 */}
      <Grid gutter="lg">
        <Grid.Col span={{ base: 12, md: 6 }}><Skeleton height={240} radius="md" /></Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}><Skeleton height={240} radius="md" /></Grid.Col>
      </Grid>

      {/* Charts row 2 */}
      <Grid gutter="lg">
        <Grid.Col span={{ base: 12, md: 6 }}><Skeleton height={220} radius="md" /></Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}><Skeleton height={220} radius="md" /></Grid.Col>
      </Grid>

      {/* Tag frequency */}
      <Skeleton height={160} radius="md" />

      {/* Anomaly table */}
      <Skeleton height={200} radius="md" />
    </Stack>
  );
}
