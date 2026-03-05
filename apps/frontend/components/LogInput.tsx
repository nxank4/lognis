"use client";

import { useState, useCallback } from "react";
import { Button, Code, Group, Paper, SegmentedControl, Stack, Text, Textarea } from "@mantine/core";
import type { LogEntry } from "@/lib/types";

interface Props {
  onSubmit: (entries: LogEntry[]) => void;
  loading: boolean;
}

type Format = "json" | "plaintext";

const PLACEHOLDER_JSON = `[
  { "level": "INFO",  "message": "Server started on port 8080",        "source": "server"  },
  { "level": "WARN",  "message": "High memory usage detected: 87%",    "source": "monitor" },
  { "level": "ERROR", "message": "Failed login attempt for user admin", "source": "auth"    }
]`;

const PLACEHOLDER_PLAIN = `INFO server Server started on port 8080
WARN monitor High memory usage detected: 87%
ERROR auth Failed login attempt for user admin`;

function parsePlaintext(text: string): LogEntry[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split(/\s+/);
      const level   = parts[0] ?? "INFO";
      const source  = parts[1] ?? "app";
      const message = parts.slice(2).join(" ") || line;
      return { level, message, source };
    });
}

function parseJson(text: string): LogEntry[] {
  const parsed = JSON.parse(text);
  if (!Array.isArray(parsed)) throw new Error("Expected a JSON array");
  return parsed as LogEntry[];
}

export default function LogInput({ onSubmit, loading }: Props) {
  const [format, setFormat]         = useState<Format>("json");
  const [text, setText]             = useState("");
  const [parseError, setParseError] = useState<string | null>(null);

  const handleSubmit = useCallback(() => {
    setParseError(null);
    try {
      const entries = format === "json" ? parseJson(text) : parsePlaintext(text);
      if (entries.length === 0) { setParseError("No log entries found."); return; }
      onSubmit(entries);
    } catch (e) {
      setParseError(e instanceof Error ? e.message : "Parse error");
    }
  }, [format, text, onSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  return (
    <Paper withBorder p="xl" radius="md" component="section" aria-label="Log entry input">
      <Stack gap="sm">
        {/* Header row */}
        <Group justify="space-between">
          <Text size="sm" c="dimmed">Paste log entries to analyze</Text>
          <SegmentedControl
            value={format}
            onChange={(v) => { setFormat(v as Format); setParseError(null); }}
            color="lognis"
            size="xs"
            data={[
              { label: "JSON",      value: "json"      },
              { label: "Plaintext", value: "plaintext" },
            ]}
          />
        </Group>

        {/* Format hint */}
        {format === "plaintext" && (
          <Text size="xs" c="dimmed">
            Format: <Code color="violet.4" fz="xs">LEVEL source message per line</Code>
          </Text>
        )}

        {/* Textarea */}
        <Textarea
          value={text}
          onChange={(e) => { setText(e.currentTarget.value); setParseError(null); }}
          onKeyDown={handleKeyDown}
          placeholder={format === "json" ? PLACEHOLDER_JSON : PLACEHOLDER_PLAIN}
          autosize
          minRows={10}
          maxRows={30}
          variant="filled"
          error={parseError}
          spellCheck={false}
          aria-label="Log entries"
          aria-invalid={!!parseError}
          styles={{
            input: {
              fontFamily: "var(--mantine-font-family-monospace)",
              fontSize: "13px",
              background: "#070b14",
              border: "1px solid #1e293b",
            },
          }}
        />

        {/* Submit row */}
        <Group justify="space-between">
          <Text size="xs" c="dimmed">Ctrl+Enter to analyze</Text>
          <Button
            onClick={handleSubmit}
            loading={loading}
            disabled={!text.trim()}
            color="lognis"
            size="sm"
          >
            Analyze
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
}
