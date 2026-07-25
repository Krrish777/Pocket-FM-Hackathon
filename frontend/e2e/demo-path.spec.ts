import { expect, test, type Page } from "@playwright/test";

/**
 * The rehearsed demo path, end to end.
 *
 * REQUIREMENTS.md §2 defines success behaviourally: a judge completes this flow
 * unprompted in under 90 seconds. This spec walks exactly that path, so a
 * regression that breaks the on-stage run fails here first. Treat a failure in
 * this file as "the demo is broken", not "a test is flaky".
 *
 *   ST-01 → E03 → CH-02 (Dev) → ALT-A → 11/20/3 → scene → ✓ → planted defect
 */

/** Assertions read English copy; the app itself defaults to Hindi. */
async function switchToEnglish(page: Page) {
  await page.getByRole("button", { name: "EN", exact: true }).click();
}

test.describe("CANON demo path", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await switchToEnglish(page);
  });

  test("walks shelf → timeline → divergence → ripple → output → defect", async ({
    page,
  }) => {
    // 1. Shelf — the authored story is clickable.
    await expect(page.getByText("The paths never taken")).toBeVisible();
    await page.getByRole("button", { name: "The Last Bench" }).click();

    // 2. Timeline — pick the character the moment belongs to.
    await expect(page.getByText("Three engineering students")).toBeVisible();
    await page.getByRole("button", { name: /Devansh Iyer/ }).click();

    // 3. Only episodes with an authored moment are selectable. E01 has none.
    await expect(page.getByRole("button", { name: "E01" })).toBeDisabled();
    await page.getByRole("button", { name: "E03" }).click();

    // 4. Divergence — the flip is gated until an alternative is chosen.
    await expect(page.getByText("Aarav reaches the roof in time")).toBeVisible();
    const flip = page.getByRole("button", { name: /FLIP THIS MOMENT/ });
    await expect(flip).toBeDisabled();

    await page.getByRole("radio").first().click();
    await expect(flip).toBeEnabled();
    await flip.click();

    // 5. Ripple — the counters must land on the rehearsed numbers.
    await expect(page.getByTestId("counter-invalidated")).toHaveText("11", {
      timeout: 20_000,
    });
    await expect(page.getByTestId("counter-held")).toHaveText("20");
    await expect(page.getByTestId("counter-new")).toHaveText("3");

    // The forward action appears only once the cascade has settled.
    const seeResult = page.getByRole("button", { name: /SEE WHAT HAPPENS/ });
    await expect(seeResult).toBeVisible({ timeout: 15_000 });
    await seeResult.click();

    // 6. Output — real generated prose, and a consistent verdict.
    const scene = page.getByTestId("scene-text");
    await expect(scene).toBeVisible({ timeout: 20_000 });
    await expect(scene).toContainText("They did not reassign the third bed");

    const badge = page.getByTestId("verifier-badge");
    await expect(badge).toHaveAttribute("data-status", "ok");
    await expect(badge).toContainText("CANON-CONSISTENT");

    // 7. Planted defect — the proof moment, one click away.
    await page.getByRole("button", { name: /RUN BROKEN BRANCH/ }).click();

    const flagged = page.getByTestId("verifier-badge");
    await expect(flagged).toHaveAttribute("data-status", "flagged", {
      timeout: 20_000,
    });
    await expect(flagged).toContainText("CONTRADICTION FLAGGED");
    // A flag without a citation is an error message, not evidence.
    await expect(flagged).toContainText("Devansh Iyer is not alive in this branch");
    await expect(flagged).toContainText("E03");
  });

  test("shows both passages side by side from the defect proof", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "The Last Bench" }).click();
    await page.getByRole("button", { name: /Devansh Iyer/ }).click();
    await page.getByRole("button", { name: "E03" }).click();
    await page.getByRole("radio").first().click();
    await page.getByRole("button", { name: /FLIP THIS MOMENT/ }).click();
    await page
      .getByRole("button", { name: /SEE WHAT HAPPENS/ })
      .click({ timeout: 25_000 });
    await page.getByRole("button", { name: /RUN BROKEN BRANCH/ }).click();

    await page.getByRole("button", { name: /VIEW BOTH PASSAGES/ }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("DRAFT CLAIM");
    await expect(dialog).toContainText("CANON SAYS");
  });

  test("presenter mode strips the header chrome", async ({ page }) => {
    const header = page.locator("header").first();
    await expect(header).toBeVisible();

    await page.getByRole("button", { name: "PRESENT" }).click();

    // REQUIREMENTS.md §12: zero visible debug/nav chrome during a dry run.
    await expect(page.getByRole("button", { name: "PRESENT" })).toBeHidden();
    await expect(page.getByRole("button", { name: "EXIT" })).toBeVisible();

    // `P` is the operator's escape hatch when the header is gone.
    await page.keyboard.press("p");
    await expect(page.getByRole("button", { name: "PRESENT" })).toBeVisible();
  });

  test("runs entirely in Hindi", async ({ page }) => {
    // The seed story is Hindi-first; the whole UI must switch, not just prose.
    await page.getByRole("button", { name: "हि" }).click();
    await expect(page.getByText("वो रास्ते जो कभी नहीं लिए गए")).toBeVisible();
    await page.getByRole("button", { name: "आख़िरी बेंच" }).click();
    await expect(page.getByRole("button", { name: /देवांश अय्यर/ })).toBeVisible();
  });
});
