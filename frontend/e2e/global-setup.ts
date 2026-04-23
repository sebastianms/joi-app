/**
 * Playwright global setup — seeds the SQLite fixture connection before E2E tests run.
 *
 * Inserts the connection row directly into joi_app.db via a Python helper script
 * (bypasses the HTTP endpoint which requires aiosqlite:// and does a live connection
 * test). The SqlAgentAdapter uses `file_path` for SQLite, so that's the field we set.
 *
 * Requires the backend running at http://127.0.0.1:8000 with MOCK_LLM_RESPONSES=true.
 */

import { execFileSync } from "child_process";
import path from "path";

export const E2E_SESSION_ID = "e2e-data-agent-session";
export const SALES_DB_PATH =
  "/home/seba/Apps/joi-app/backend/tests/fixtures/sales_sample.db";

// Quickstart scenarios use dedicated sessions to isolate state across tests.
export const QUICKSTART_SESSIONS = [
  `${E2E_SESSION_ID}-kpi`,
  `${E2E_SESSION_ID}-empty`,
  `${E2E_SESSION_ID}-pref`,
  `${E2E_SESSION_ID}-incompat`,
] as const;

const PYTHON = path.resolve(__dirname, "../../backend/.venv/bin/python");
const SEED_SCRIPT = path.resolve(__dirname, "seed-e2e-db.py");

export default async function globalSetup() {
  execFileSync(
    PYTHON,
    [SEED_SCRIPT, SALES_DB_PATH, E2E_SESSION_ID, ...QUICKSTART_SESSIONS],
    { stdio: "inherit" },
  );
}
