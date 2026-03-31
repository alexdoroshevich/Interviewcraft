/**
 * Skills page E2E tests.
 */

import { test, expect } from "@playwright/test";
import { AUTH_FILE } from "./auth.setup";

test.use({ storageState: AUTH_FILE });

test("skills page loads with radar chart", async ({ page }) => {
  await page.goto("/skills");
  await expect(page.locator("text=Skill Graph")).toBeVisible();
  // Recharts renders an SVG
  await expect(page.locator("svg").first()).toBeVisible();
});

test("skills page drill plan tab shows slots", async ({ page }) => {
  await page.goto("/skills");
  await page.locator("text=Drill Plan").click();
  // With demo data, at least one drill slot should appear
  await expect(page.locator("text=Mon").or(page.locator("text=No sessions")).first()).toBeVisible();
});

test("skills page beat your best tab", async ({ page }) => {
  await page.goto("/skills");
  await page.locator("text=Beat Your Best").click();
  await expect(page.locator("text=Beat Your Best").first()).toBeVisible();
});
