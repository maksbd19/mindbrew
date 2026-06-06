import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      colors: {
        page: "#09090b",
        surface: {
          DEFAULT: "#111113",
          raised: "#18181b",
          hover: "#1c1c20",
        },
        border: {
          DEFAULT: "#27272a",
          subtle: "#1f1f23",
        },
        foreground: "#fafafa",
        muted: {
          DEFAULT: "#a1a1aa",
          light: "#d4d4d8",
        },
        accent: {
          DEFAULT: "#60a5fa",
          muted: "#93c5fd",
        },
        primary: {
          DEFAULT: "#2563eb",
          hover: "#1d4ed8",
        },
        secondary: {
          DEFAULT: "#27272a",
          hover: "#3f3f46",
        },
        danger: "#f87171",
        warning: "#fbbf24",
        success: "#4ade80",
        chip: {
          awaiting: { bg: "#422006", text: "#fcd34d" },
          running: { bg: "#172554", text: "#93c5fd" },
          completed: { bg: "#052e16", text: "#86efac" },
          interrupted: { bg: "#450a0a", text: "#fca5a5" },
        },
        enzyme: {
          bg: "#1e293b",
          border: "#2563eb",
        },
        verified: "#4ade80",
        unverified: "#fbbf24",
        invalid: "#f87171",
      },
      boxShadow: {
        card: "0 1px 2px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.03)",
      },
      typography: {
        DEFAULT: {
          css: {
            color: "#fafafa",
            a: { color: "#60a5fa" },
            strong: { color: "#fafafa" },
            h1: { color: "#fafafa" },
            h2: { color: "#fafafa" },
            h3: { color: "#fafafa" },
            h4: { color: "#fafafa" },
            code: {
              color: "#fafafa",
              backgroundColor: "#09090b",
              border: "1px solid #27272a",
              borderRadius: "0.25rem",
              padding: "0.1rem 0.35rem",
              fontWeight: "400",
            },
            "code::before": { content: '""' },
            "code::after": { content: '""' },
            pre: {
              backgroundColor: "#09090b",
              border: "1px solid #27272a",
              color: "#fafafa",
            },
            blockquote: {
              color: "#d4d4d8",
              borderLeftColor: "#2563eb",
            },
            hr: { borderColor: "#27272a" },
            th: {
              backgroundColor: "#18181b",
              color: "#d4d4d8",
            },
            "thead th": {
              borderBottomColor: "#27272a",
            },
            "tbody td, tfoot td": {
              borderBottomColor: "#27272a",
            },
          },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
