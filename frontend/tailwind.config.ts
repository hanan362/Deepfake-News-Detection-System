import type { Config } from "tailwindcss";

// Colours come from CSS variables (see src/styles/index.css) so the light/dark theme switch is one attribute.
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: token("bg"), panel: token("panel"), raised: token("raised"), line: token("line"),
        ink: token("ink"), "ink-2": token("ink-2"), "ink-3": token("ink-3"),
        primary: token("primary"), "on-primary": token("on-primary"), link: token("link"), cyan: token("cyan"), violet: token("violet"),
        ok: token("ok"), warn: token("warn"), bad: token("bad"),
        rail: token("rail"), "rail-ink": token("rail-ink"), "rail-dim": token("rail-dim"),
        "band-real": token("band-real"), "band-fake": token("band-fake"), "band-unsure": token("band-unsure"), "band-flag": token("band-flag"),
      },
      fontFamily: {
        sans: ['"Instrument Sans Variable"', "ui-sans-serif", "system-ui", "sans-serif"],
        display: ['"Bricolage Grotesque Variable"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: { exhibit: "6px", panel: "14px", control: "10px" },
      maxWidth: { prose: "68ch" },
    },
  },
  plugins: [],
} satisfies Config;
