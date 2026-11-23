import { expect, test } from "@playwright/test";
import { ARTICLE_TEXT } from "./fixtures/article";
import { registerAndLogin } from "./helpers";

// Real server and the real inference model. Only the news search is canned (see run_backend.py), so no internet is needed.
const REPORTED = "New ferry terminal to open in March";
const OPPOSITE = "Harbour authority confirms new ferry terminal will open in March";

async function analyse(page: import("@playwright/test").Page, headline: string | null) {
  await page.goto("/analyze/text");
  if (headline) await page.getByLabel("Headline").fill(headline);
  await page.getByLabel("Article text").fill(ARTICLE_TEXT);
  await page.getByRole("button", { name: "Analyse text" }).click();
  await expect(page).toHaveURL(/\/analysis\/\d+$/);
  await page.getByTestId("verdict").waitFor();
}

test.describe("headline compared with news reports", () => {
  test.beforeEach(async ({ request }) => {
    const health = await (await request.get("/api/v1/modules")).json();
    test.skip(health.models.find((m: { module: string }) => m.module === "evidence")?.status !== "pretrained", "the inference packages are not installed here");
  });

  test("a headline that a listed outlet also ran is shown as reported, and never as proof", async ({ page }) => {
    await registerAndLogin(page);
    await analyse(page, REPORTED);
    const panel = page.getByTestId("corroboration");
    await expect(panel).toHaveAttribute("data-status", "corroborated");
    await expect(panel.getByTestId("corroboration-outlet")).toContainText("Reuters");
    await expect(panel.getByTestId("corroboration-outlet")).toContainText("Says the same");
    await expect(page.getByTestId("verdict")).not.toHaveText("Likely Fake");
    await expect(page.getByText(/shows that a story was reported, not that it is true/)).toBeVisible();
    await panel.getByText("How this is decided and what it cannot show").click();
    await expect(panel).toContainText("Only the headline is compared, not the article");
    const pdf = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download PDF" }).click()]);
    expect(pdf[0].suggestedFilename()).toMatch(/^analysis-\d+\.pdf$/);
  });

  test("a very similar headline that says the opposite is flagged as different, never as fake", async ({ page }) => {
    await registerAndLogin(page);
    await analyse(page, OPPOSITE);
    const panel = page.getByTestId("corroboration");
    await expect(panel).toHaveAttribute("data-status", "disputed");
    await expect(panel.getByTestId("corroboration-outlet")).toContainText("Says the opposite");
    await expect(page.getByTestId("verdict")).not.toHaveText("Likely Fake");
  });

  test("a headline nobody ran gives 'no matching report', which is not held against it", async ({ page }) => {
    await registerAndLogin(page);
    await analyse(page, "Residents celebrate the reopening of the old town library");
    const panel = page.getByTestId("corroboration");
    await expect(panel).toHaveAttribute("data-status", "not_found");
    await expect(panel).toContainText("does not mean the story is false");
  });

  test("without a headline nothing is searched and the page says so", async ({ page }) => {
    await registerAndLogin(page);
    await analyse(page, null);
    await expect(page.getByTestId("corroboration")).toHaveAttribute("data-status", "skipped");
    await expect(page.getByTestId("corroboration")).toContainText("No headline was given");
  });

  test("a page on a listed outlet's own site is never confirmed by that outlet itself, and is never called fake", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/url");
    await page.getByLabel("Article address").fill("http://www.reuters.com/ferry-terminal");
    await page.getByRole("button", { name: "Read and analyse" }).click();
    await page.getByTestId("verdict").waitFor();
    // the stand-in news search has a Reuters headline for this story; it must not count because the page itself is on reuters.com
    await expect(page.getByTestId("corroboration")).toHaveAttribute("data-status", "not_found");
    await expect(page.getByTestId("corroboration")).toContainText("Reuters, the site this article came from, was not counted");
    await expect(page.getByTestId("verdict")).not.toHaveText("Likely Fake");
    await expect(page.getByTestId("source-outcome")).toHaveAttribute("data-assessment", "recognised_publisher");
  });

  test("an article read from an unlisted website is compared with the listed outlets", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/url");
    await page.getByLabel("Article address").fill("http://news.example/ferry-terminal");
    await page.getByRole("button", { name: "Read and analyse" }).click();
    await page.getByTestId("verdict").waitFor();
    await expect(page.getByTestId("corroboration")).toHaveAttribute("data-status", "corroborated");
    await expect(page.getByTestId("corroboration-outlet")).toContainText("Reuters");
  });
});
