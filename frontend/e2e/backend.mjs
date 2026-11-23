// Starts the real FastAPI server on a throw-away database and storage folder for the end-to-end tests.
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.resolve(here, "..", "..", "backend");
const tmp = mkdtempSync(path.join(tmpdir(), "ddn-e2e-"));
const port = process.env.E2E_API_PORT ?? "8765";

// run_backend.py starts the same server, plus a stand-in news site for the "read a news address" tests.
const child = spawn(process.env.E2E_PYTHON ?? "python3", [path.join(here, "run_backend.py")], {
  cwd: backendDir,
  stdio: "inherit",
  env: {
    ...process.env,
    E2E_BACKEND_DIR: backendDir,
    E2E_API_PORT: port,
    ENVIRONMENT: "test",
    DATABASE_URL: `sqlite:///${tmp.replaceAll("\\", "/")}/e2e.db`,
    STORAGE_DIR: path.join(tmp, "storage"),
    SECRET_KEY: "e2e-only-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz",
    BCRYPT_ROUNDS: "4",
    EXPOSE_RESET_TOKEN: "true",
    ADMIN_EMAIL: "admin@example.com",
    ADMIN_PASSWORD: "AdminPass123",
    AUTH_RATE_LIMIT_PER_MINUTE: "10000",
    RATE_LIMIT_PER_MINUTE: "10000",
  },
});

const stop = () => {
  child.kill("SIGTERM");
  setTimeout(() => {
    try { rmSync(tmp, { recursive: true, force: true }); } catch { /* best effort */ }
    process.exit(0);
  }, 500);
};
process.on("SIGTERM", stop);
process.on("SIGINT", stop);
child.on("exit", (code) => process.exit(code ?? 1));
