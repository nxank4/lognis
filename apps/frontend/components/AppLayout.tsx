"use client";

import { AppShell } from "@mantine/core";
import Header from "./Header";

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell header={{ height: 56 }} padding={0}>
      <AppShell.Header
        style={{ background: "#0f1729", borderBottom: "1px solid #1e293b" }}
      >
        <Header />
      </AppShell.Header>
      <AppShell.Main>{children}</AppShell.Main>
    </AppShell>
  );
}
