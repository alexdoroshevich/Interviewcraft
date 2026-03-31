/**
 * Auth setup — runs once before all E2E tests.
 * Logs in as demo user and saves auth state to disk.
 *
 * Prereq: demo user seeded via `python scripts/seed_demo.py`
 */

import { test as setup, expect } from "@playwright/test";
import path from "path";

export const AUTH_FILE = path.join(__dirname, "../.playwright/auth.json");

const DEMO_EMAIL = "demo@interviewcraft.dev";
const DEMO_PASSWORD = "demo1234";

setup("authenticate as demo user", async ({ page, request }) => {
  // Call the backend auth API directly to get a token
  const res = await request.post("http://localhost:8080/api/v1/auth/login", {
    data: { email: DEMO_EMAIL, password: DEMO_PASSWORD },
  });
  expect(res.status()).toBe(200);
  const body = await res.json();
  const token: string = body.access_token;

  // Navigate to the app and inject the token into localStorage
  await page.goto("/");
  await page.evaluate((t) => localStorage.setItem("access_token", t), token);

  // Verify we can reach the dashboard
  await page.goto("/dashboard");
  await expect(page.locator("text=Dashboard")).toBeVisible();

  // Save auth state for reuse
  await page.context().storageState({ path: AUTH_FILE });
});
