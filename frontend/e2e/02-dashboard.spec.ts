/**
 * Dashboard E2E tests — requires demo user to be seeded.
 */

import { test, expect } from "@playwright/test";
import { AUTH_FILE } from "./auth.setup";

test.use({ storageState: AUTH_FILE });

test("dashboard loads with stats", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.locator("text=Sessions")).toBeVisible();
  await expect(page.locator("text=Avg Score")).toBeVisible();
  await expect(page.locator("text=Skills Tracked")).toBeVisible();
  await expect(page.locator("text=Stories")).toBeVisible();
});

test("dashboard shows readiness meter", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.locator("text=Readiness Estimate")).toBeVisible();
});

test("dashboard shows recent sessions list", async ({ page }) => {
  await page.goto("/dashboard");
  // Demo data has 10 sessions — at least some should appear
  await expect(page.locator("text=Behavioral").first()).toBeVisible();
});

test("dashboard links to skills page", async ({ page }) => {
  await page.goto("/dashboard");
  await page.locator("text=Skills →").click();
  await expect(page).toHaveURL(/\/skills/);
});

test("dashboard links to all sessions", async ({ page }) => {
  await page.goto("/dashboard");
  await page.locator("text=All sessions →").click();
  await expect(page).toHaveURL(/\/sessions/);
});
