import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E test config.
 *
 * Usage:
 *   npm run test:e2e              — headless Chromium
 *   npm run test:e2e:ui           — interactive UI mode
 *   HEADED=1 npm run test:e2e     — headed browser
 *
 * Prerequisites:
 *   1. npx playwright install chromium
 *   2. Backend running on :8080, frontend on :3000
 *   3. Demo user seeded: python scripts/seed_demo.py
 */

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // sessions have state — run sequentially
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "html",

  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Start the server automatically.
  // CI: use the pre-built production server (npm run build must run first).
  // Local: reuse an existing dev server if one is already running.
  webServer: {
    // CI: Next.js is built with output:standalone, so next start won't work.
    // Use the standalone server directly. Local dev reuses an existing server.
    command: process.env.CI
      ? "node .next/standalone/server.js"
      : "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    env: process.env.CI ? { PORT: "3000", HOSTNAME: "0.0.0.0" } : {},
  },
});
