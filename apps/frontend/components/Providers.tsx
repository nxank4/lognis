"use client";

import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { ModalsProvider } from "@mantine/modals";
import { theme, cssVariablesResolver } from "@/lib/theme";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <MantineProvider
      theme={theme}
      defaultColorScheme="dark"
      cssVariablesResolver={cssVariablesResolver}
    >
      <ModalsProvider>
        <Notifications
          position="bottom-right"
          zIndex={1000}
          limit={5}
          styles={{
            notification: {
              fontFamily: "var(--mantine-font-family)",
              background: "#0f1729",
              border: "1px solid #1e293b",
            },
          }}
        />
        {children}
      </ModalsProvider>
    </MantineProvider>
  );
}
