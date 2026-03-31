/**
 * Story bank E2E tests.
 */

import { test, expect } from "@playwright/test";
import { AUTH_FILE } from "./auth.setup";

test.use({ storageState: AUTH_FILE });

test("stories page loads story list", async ({ page }) => {
  await page.goto("/stories");
  await expect(page.locator("text=Story Bank")).toBeVisible();
  // Demo data has 5 stories
  await expect(page.locator("text=Led Database Migration").first()).toBeVisible();
});

test("stories coverage map shows competency grid", async ({ page }) => {
  await page.goto("/stories");
  await page.locator("text=Coverage Map").click();
  await expect(page.locator("text=Coverage Map")).toBeVisible();
  // At least one competency status badge
  await expect(
    page.locator("text=strong").or(page.locator("text=weak")).or(page.locator("text=gap")).first()
  ).toBeVisible();
});

test("add story form opens and validates", async ({ page }) => {
  await page.goto("/stories");
  await page.locator("text=+ Add story manually").click();
  await expect(page.locator("text=New Story")).toBeVisible();
  // Save button disabled without input
  const saveBtn = page.locator("text=Save Story");
  await expect(saveBtn).toBeDisabled();
});
