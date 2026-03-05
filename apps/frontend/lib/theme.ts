import {
  createTheme,
  type MantineColorsTuple,
  type CSSVariablesResolver,
} from "@mantine/core";

// ── Primary (Lognis blue) ────────────────────────────────────────────────────
const lognis: MantineColorsTuple = [
  "#eff6ff",
  "#dbeafe",
  "#bfdbfe",
  "#93c5fd",
  "#60a5fa",
  "#3b82f6", // 5 — primary
  "#2563eb", // 6 — hover
  "#1d4ed8",
  "#1e40af",
  "#1e3a8a",
];

// ── Dark scale — Lognis cyber palette (index 0 = lightest text → 9 = deepest bg) ──
const dark: MantineColorsTuple = [
  "#e2e8f0", // 0  foreground
  "#94a3b8", // 1  muted-fg  (slate-400)
  "#64748b", // 2  dimmed
  "#475569", // 3
  "#334155", // 4
  "#1e293b", // 5  card-border / muted-bg
  "#162033", // 6  input filled bg
  "#0f1729", // 7  card / Paper bg   ← Mantine Paper default in dark mode
  "#0c1220", // 8
  "#0a0e1a", // 9  page background
];

export const theme = createTheme({
  primaryColor: "lognis",
  primaryShade: 5,
  colors: { lognis, dark },

  fontFamily:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
  fontFamilyMonospace:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, monospace',

  defaultRadius: "md",

  headings: {
    fontFamily:
      'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, monospace',
    fontWeight: "700",
  },

  components: {
    Paper: {
      defaultProps: { bg: "dark.7" },
    },
    Card: {
      defaultProps: { bg: "dark.7" },
    },
    Table: {
      defaultProps: {
        fz: "xs",
        verticalSpacing: "xs",
      },
    },
  },
});

// ── CSS variable overrides for dark mode ─────────────────────────────────────
export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {},
  dark: {
    "--mantine-color-body":           "#0a0e1a", // page background
    "--mantine-color-default":        "#0f1729", // default component bg
    "--mantine-color-default-border": "#1e293b", // default border
    "--mantine-color-dimmed":         "#94a3b8", // dimmed text
    "--mantine-color-placeholder":    "#475569", // input placeholder
    "--mantine-color-text":           "#e2e8f0", // primary text
    "--mantine-color-anchor":         "#60a5fa", // link color
  },
  light: {
    "--mantine-color-body": "#f8fafc",
  },
});
