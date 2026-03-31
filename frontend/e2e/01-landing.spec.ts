/**
 * Landing page smoke tests.
 * No auth required.
 */

import { test, expect } from "@playwright/test";

test("landing page loads with hero copy", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Stop practicing blindly");
  await expect(page.locator("text=Start practicing free")).toBeVisible();
  await expect(page.locator("text=The Closed Training Loop")).toBeVisible();
});

test("landing page feature tiles present", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("text=Evidence-backed Scoring")).toBeVisible();
  await expect(page.locator("text=Rewind Micro-Practice")).toBeVisible();
  await expect(page.locator("text=Negotiation Simulator")).toBeVisible();
});

test("CTA links to new session", async ({ page }) => {
  await page.goto("/");
  const cta = page.locator("text=Start practicing free").first();
  await expect(cta).toHaveAttribute("href", /sessions\/new/);
});
