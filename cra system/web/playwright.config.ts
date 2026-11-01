import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: [["line"]],
  use: {
    baseURL: process.env.CRA_E2E_BASE_URL ?? "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure"
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ],
  webServer: [
    {
      command:
        "uv run --project .. --frozen uvicorn cra_app.main:app --app-dir ../backend --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health/live",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        CRA_API_PROXY_TARGET: "http://127.0.0.1:8000"
      }
    }
  ]
});
