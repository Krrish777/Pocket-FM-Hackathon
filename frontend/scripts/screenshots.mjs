#!/usr/bin/env node
/**
 * Capture each screen for visual review.
 *
 * Not part of the test suite — this is a reviewing aid. Point it at a running
 * dev server: `node scripts/screenshots.mjs <outDir>`.
 */

import { mkdirSync } from "node:fs";
import { join } from "node:path";

import { chromium } from "@playwright/test";

const OUT = process.argv[2] ?? "./screenshots";
const BASE = process.env.BASE_URL ?? "http://localhost:3000";

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });

const shot = async (name) => {
  await page.screenshot({ path: join(OUT, `${name}.png`) });
  console.log(`captured ${name}`);
};

await page.goto(BASE);
await page.getByRole("button", { name: "EN", exact: true }).click();
await page.waitForTimeout(600);
await shot("1-shelf");

await page.getByRole("button", { name: "The Last Bench" }).click();
await page.getByRole("button", { name: /Devansh Iyer/ }).click();
await page.waitForTimeout(700);
await shot("2-timeline");

await page.getByRole("button", { name: "E03" }).click();
await page.getByRole("radio").first().click();
await page.waitForTimeout(600);
await shot("3-divergence");

await page.getByRole("button", { name: /FLIP THIS MOMENT/ }).click();
// Let the full 2.4s cascade settle before capturing.
await page.getByRole("button", { name: /SEE WHAT HAPPENS/ }).waitFor({ timeout: 25_000 });
await page.waitForTimeout(400);
await shot("4-ripple");

await page.getByRole("button", { name: /SEE WHAT HAPPENS/ }).click();
await page.getByTestId("scene-text").waitFor({ timeout: 25_000 });
await page.waitForTimeout(600);
await shot("5-output");

await page.getByRole("button", { name: /RUN BROKEN BRANCH/ }).click();
// Wait for the *flagged* badge specifically — the outgoing Output screen still
// has its own badge in the DOM mid-transition, so waiting on the testid alone
// resolves instantly and captures a loading frame.
await page.locator('[data-testid="verifier-badge"][data-status="flagged"]').waitFor({
  timeout: 25_000,
});
await page.waitForTimeout(800);
await shot("6-defect");

// Hindi, the default locale — checks Devanagari rendering end to end.
await page.goto(BASE);
await page.waitForTimeout(600);
await shot("7-shelf-hindi");

await browser.close();
console.log(`\nScreenshots written to ${OUT}`);
