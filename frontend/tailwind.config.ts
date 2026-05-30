import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111317",
        line: "#d8dde6",
        surface: "#f5f7fa",
        accent: "#00a88f",
        signal: "#ff6b35",
        cobalt: "#2563eb",
        night: "#171a21",
      },
    },
  },
  plugins: [],
};

export default config;
