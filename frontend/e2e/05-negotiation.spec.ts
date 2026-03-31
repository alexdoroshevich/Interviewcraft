/**
 * Negotiation simulator E2E tests.
 */

import { test, expect } from "@playwright/test";
import { AUTH_FILE } from "./auth.setup";

test.use({ storageState: AUTH_FILE });

test("negotiation page shows setup form", async ({ page }) => {
  await page.goto("/negotiation");
  await expect(page.locator("text=Setup Negotiation Practice")).toBeVisible();
  await expect(page.locator("label:has-text('Company')")).toBeVisible();
  await expect(page.locator("label:has-text('Their Offer')")).toBeVisible();
});

test("negotiation start button disabled without required fields", async ({ page }) => {
  await page.goto("/negotiation");
  const btn = page.locator("text=Start Negotiation Session");
  await expect(btn).toBeDisabled();
});

test("negotiation history shows past sessions", async ({ page }) => {
  await page.goto("/negotiation");
  // Demo data has 1 negotiation session
  await expect(page.locator("text=Past Sessions").or(page.locator("text=Acme Corp")).first()).toBeVisible();
});
