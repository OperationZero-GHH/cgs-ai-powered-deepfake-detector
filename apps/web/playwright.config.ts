import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const runId = `pw-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
const e2eWebDir = process.env.E2E_WEB_DIR;
const e2eWebDirArg = e2eWebDir ? ` -E2EWebDir "${e2eWebDir}"` : "";
const nodeFirstPath = `${path.dirname(process.execPath)}${path.delimiter}${process.env.PATH ?? ""}`;
const e2eStopFile = path.resolve(process.cwd(), `../../.run/${runId}.stop`);
process.env.E2E_STOP_FILE = e2eStopFile;

export default defineConfig({
  globalTeardown: "./e2e/global-teardown.ts",
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  timeout: 60_000,
  expect: { timeout: 12_000 },
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ..\\..\\run.ps1 -E2ETest${e2eWebDirArg}`,
    cwd: ".",
    url: "http://127.0.0.1:3100",
    env: { E2E_RUN_ID: runId, E2E_STOP_FILE: e2eStopFile, PATH: nodeFirstPath, ...(e2eWebDir ? { E2E_WEB_DIR: e2eWebDir } : {}) },
    timeout: 600_000,
    reuseExistingServer: false,
    stdout: "pipe",
    stderr: "pipe",
  },
});
