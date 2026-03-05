import type { Metadata } from "next";
import { ColorSchemeScript } from "@mantine/core";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "@mantine/nprogress/styles.css";
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { Providers } from "@/components/Providers";
import { AppLayout } from "@/components/AppLayout";
import { RouterTransition } from "@/components/RouterTransition";
import { Suspense } from "react";

export const metadata: Metadata = {
  title: "Lognis — AI Agent Log Forensics",
  description: "Forensic risk analysis for AI agent logs",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <head>
          <ColorSchemeScript defaultColorScheme="dark" />
        </head>
        <body>
          <a href="#main" className="skip-to-main">
            Skip to main content
          </a>
          <Providers>
            <Suspense>
              <RouterTransition />
            </Suspense>
            <AppLayout>{children}</AppLayout>
          </Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
