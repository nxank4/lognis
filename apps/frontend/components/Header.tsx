"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ActionIcon, Button, Group, Text, Tooltip } from "@mantine/core";
import { useUser, SignInButton, UserButton } from "@clerk/nextjs";

function IconHistory() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function IconGithub() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  );
}

export default function Header() {
  const { isLoaded, user } = useUser();
  const pathname           = usePathname();
  const onHistory          = pathname === "/history";

  return (
    <Group h="100%" px={{ base: "md", md: "xl" }} justify="space-between">

      {/* ── Logo ── */}
      <Button
        component={Link}
        href="/"
        variant="subtle"
        color="gray"
        px={6}
        styles={{ root: { height: "auto" } }}
        aria-label="Lognis — home"
      >
        <Group gap={8}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect width="24" height="24" rx="5" fill="#3b82f6" />
            <rect x="5" y="7"  width="14" height="2" rx="1" fill="white" opacity="0.9" />
            <rect x="5" y="11" width="10" height="2" rx="1" fill="white" opacity="0.7" />
            <rect x="5" y="15" width="12" height="2" rx="1" fill="white" opacity="0.5" />
          </svg>
          <Text fw={700} size="sm" style={{ letterSpacing: "-0.01em" }}>
            Lognis
          </Text>
        </Group>
      </Button>

      {/* ── Nav + Auth ── */}
      <Group gap={4}>

        {/* History — only when signed in */}
        {isLoaded && user && (
          <Tooltip label="Analysis history" withArrow position="bottom" openDelay={400}>
            <Button
              component={Link}
              href="/history"
              variant={onHistory ? "light" : "subtle"}
              color={onHistory ? "lognis" : "gray"}
              size="xs"
              leftSection={<IconHistory />}
            >
              History
            </Button>
          </Tooltip>
        )}

        {/* GitHub */}
        <Tooltip label="View on GitHub" withArrow position="bottom" openDelay={400}>
          <ActionIcon
            component="a"
            href="https://github.com/nxank4/lognis"
            target="_blank"
            rel="noopener noreferrer"
            variant="subtle"
            color="gray"
            size="md"
            aria-label="View source on GitHub"
          >
            <IconGithub />
          </ActionIcon>
        </Tooltip>

        {/* Clerk auth */}
        {isLoaded && (
          user ? (
            <UserButton />
          ) : (
            <Tooltip label="Sign in to save history" withArrow position="bottom" openDelay={400}>
              <div>
                <SignInButton mode="modal">
                  <Button size="xs" color="lognis" variant="filled">
                    Sign in
                  </Button>
                </SignInButton>
              </div>
            </Tooltip>
          )
        )}
      </Group>

    </Group>
  );
}
