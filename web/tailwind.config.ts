import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        page: "#0f1117",
        surface: "#1a1d27",
        "surface-raised": "#141824",
        border: "#2a2f3d",
        foreground: "#e8eaed",
        muted: "#9aa0a6",
        "muted-light": "#c5c8ce",
        accent: "#7eb8ff",
        primary: {
          DEFAULT: "#3b6cff",
          hover: "#2952cc",
        },
        secondary: {
          DEFAULT: "#2a2f3d",
          hover: "#343a4a",
        },
        danger: "#ff8a8a",
        warning: "#ffd866",
        success: "#8fd4a8",
        chip: {
          awaiting: { bg: "#5c4a00", text: "#ffd866" },
          running: { bg: "#1a3050", text: "#7eb8ff" },
          completed: { bg: "#1a3d2a", text: "#8fd4a8" },
          interrupted: { bg: "#3d1a1a", text: "#ff8a8a" },
        },
        enzyme: {
          bg: "#2a3550",
          border: "#3b6cff",
        },
        verified: "#6dd58c",
        unverified: "#f0c040",
        invalid: "#ff8a8a",
      },
      typography: {
        DEFAULT: {
          css: {
            color: "#e8eaed",
            a: { color: "#7eb8ff" },
            strong: { color: "#e8eaed" },
            h1: { color: "#e8eaed" },
            h2: { color: "#e8eaed" },
            h3: { color: "#e8eaed" },
            h4: { color: "#e8eaed" },
            code: {
              color: "#e8eaed",
              backgroundColor: "#0f1117",
              border: "1px solid #2a2f3d",
              borderRadius: "0.25rem",
              padding: "0.1rem 0.35rem",
              fontWeight: "400",
            },
            "code::before": { content: '""' },
            "code::after": { content: '""' },
            pre: {
              backgroundColor: "#0f1117",
              border: "1px solid #2a2f3d",
              color: "#e8eaed",
            },
            blockquote: {
              color: "#c5c8ce",
              borderLeftColor: "#3b6cff",
            },
            hr: { borderColor: "#2a2f3d" },
            th: {
              backgroundColor: "#141824",
              color: "#c5c8ce",
            },
            "thead th": {
              borderBottomColor: "#2a2f3d",
            },
            "tbody td, tfoot td": {
              borderBottomColor: "#2a2f3d",
            },
          },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
