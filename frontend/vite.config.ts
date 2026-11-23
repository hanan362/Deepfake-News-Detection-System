/// <reference types="vitest/config" />
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs on :8000. Requests to /api are proxied so the browser sees one origin (no CORS needed).
const API_TARGET = process.env.VITE_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { port: 5173, proxy: { "/api": { target: API_TARGET, changeOrigin: true } } },
  preview: { port: 4173, proxy: { "/api": { target: API_TARGET, changeOrigin: true } } },
  build: { sourcemap: false, chunkSizeWarningLimit: 900 },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/tests/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
