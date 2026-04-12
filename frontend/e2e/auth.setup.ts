/**
 * Auth setup — runs once before all E2E tests.
 * Logs in as demo user via page.request (sets httpOnly refresh_token cookie),
 * then navigates to dashboard so useAuth calls tryRefreshToken() and the
 * access token is in module memory for subsequent test interactions.
 *
 * Prereq: demo user seeded via `python scripts/seed_demo.py`
 */

import { test as setup, expect } from "@playwright/test";
import path from "path";

export const AUTH_FILE = path.join(__dirname, "../.playwright/auth.json");

const DEMO_EMAIL = "demo@interviewcraft.dev";
const DEMO_PASSWORD = "demo1234";

setup("authenticate as demo user", async ({ page }) => {
  // POST via page.request so the httpOnly refresh_token cookie lands in
  // the browser context — localStorage injection is no longer used.
  const res = await page.request.post("http://localhost:8080/api/v1/auth/login", {
    data: { email: DEMO_EMAIL, password: DEMO_PASSWORD },
  });
  expect(res.status()).toBe(200);

  // Navigate to the app — useAuth calls tryRefreshToken() using the cookie
  // and stores the access token in the module-level in-memory variable.
  await page.goto("/dashboard");
  await expect(page.locator("text=Dashboard")).toBeVisible();

  // Save auth state (includes cookies) for reuse across tests.
  await page.context().storageState({ path: AUTH_FILE });
});
