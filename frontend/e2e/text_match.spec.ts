import { expect, test } from "@playwright/test";
import { ARTICLE_HEADLINE, ARTICLE_TEXT } from "./fixtures/article";
import { registerAndLogin } from "./helpers";

// Real server and the real inference model. Only the news search is canned (see run_backend.py), so no internet is needed.
// The headline below is one that the canned search reports at Reuters, so the headline check on its own would confirm it.
const REPORTED = "New ferry terminal to open in March";
const ELSEWHERE =
  "A swimmer crossed the channel on Saturday in a record time of nine hours, according to the organisers of the event. Rough seas and cold water " +
  "slowed the early part of the swim, but the weather improved after midday. Supporters followed the swimmer by boat and cheered from the shore " +
  "when the crossing was completed late in the evening. The organisers said that more than forty swimmers had entered this year.";

async function analyse(page: import("@playwright/test").Page, headline: string, text: string) {
  await page.goto("/analyze/text");
  await page.getByLabel("Headline").fill(headline);
  await page.getByLabel("Article text").fill(text);
  await page.getByRole("button", { name: "Analyse text" }).click();
  await expect(page).toHaveURL(/\/analysis\/\d+$/);
  await page.getByTestId("verdict").waitFor();
}

test.describe("text compared with its headline", () => {
  test.beforeEach(async ({ request }) => {
    const health = await (await request.get("/api/v1/modules")).json();
    test.skip(health.models.find((m: { module: string }) => m.module === "evidence")?.status !== "pretrained", "the inference packages are not installed here");
  });

  test("a real headline over a text about something else is not called real", async ({ page }) => {
    await registerAndLogin(page);
    await analyse(page, REPORTED, ELSEWHERE);
    await expect(page.getByTestId("corroboration")).toHaveAttribute("data-status", "corroborated"); // the headline alone is confirmed ...
    const match = page.getByTestId("text-match");
    await expect(match).toHaveAttribute("data-status", "unrelated"); // ... but the text under it is about something else
    await expect(page.getByTestId("text-match-status")).toHaveText("The text is about something else");
    await expect(page.getByTestId("text-match-best")).toContainText("swimmer");
    await expect(page.getByTestId("verdict")).toHaveText("Unverified");
    await match.getByText("How this is decided and what it cannot show").click();
    await expect(match).toContainText("false details further on");
    const pdf = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download PDF" }).click()]);
    expect(pdf[0].suggestedFilename()).toMatch(/^analysis-\d+\.pdf$/);
  });

  test("a headline over its own text is read as matching, and never as fake", async ({ page }) => {
    await registerAndLogin(page);
    await analyse(page, ARTICLE_HEADLINE, ARTICLE_TEXT);
    await expect(page.getByTestId("text-match")).toHaveAttribute("data-status", "consistent");
    await expect(page.getByTestId("text-match-best")).toContainText("city council voted");
    await expect(page.getByTestId("verdict")).not.toHaveText("Likely Fake");
  });

  test("without a headline there is nothing to compare, and no panel is shown", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/text");
    await page.getByLabel("Article text").fill(ARTICLE_TEXT);
    await page.getByRole("button", { name: "Analyse text" }).click();
    await page.getByTestId("verdict").waitFor();
    await expect(page.getByTestId("text-match")).toHaveCount(0);
  });
});
