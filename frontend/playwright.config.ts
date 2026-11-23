import { defineConfig } from "@playwright/test";

const API_PORT = process.env.E2E_API_PORT ?? "8765";
const WEB_PORT = process.env.E2E_WEB_PORT ?? "4173";

/**
 * End-to-end tests run the real server (real database, real text model, real image analysis) behind the built interface.
 * Set E2E_CHROME_PATH to use an installed Chrome or Chromium instead of Playwright's own download.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: process.env.E2E_CHROME_PATH ? { executablePath: process.env.E2E_CHROME_PATH, args: ["--no-sandbox"] } : {},
  },
  webServer: [
    { command: "node e2e/backend.mjs", url: `http://127.0.0.1:${API_PORT}/api/v1/health`, timeout: 90_000, reuseExistingServer: false },
    {
      command: `npx vite build && npx vite preview --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      timeout: 120_000,
      reuseExistingServer: false,
      env: { VITE_PROXY_TARGET: `http://127.0.0.1:${API_PORT}` },
    },
  ],
});
