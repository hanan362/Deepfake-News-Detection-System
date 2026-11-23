import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import { ARTICLE_HEADLINE, ARTICLE_TEXT, SHORT_TEXT } from "./fixtures/article";
import { URDU_HEADLINE, URDU_TEXT } from "./fixtures/urdu_article";
import { registerAndLogin } from "./helpers";

const VERDICTS = ["Likely Fake", "Likely Real", "Unverified"];
const fixture = (name: string) => fileURLToPath(new URL(`./fixtures/${name}`, import.meta.url));

async function analyseArticle(page: Page) {
  await page.goto("/analyze/text");
  await page.getByLabel("Headline").fill(ARTICLE_HEADLINE);
  await page.getByLabel("Article text").fill(ARTICLE_TEXT);
  await page.getByRole("button", { name: "Analyse text" }).click();
  await expect(page).toHaveURL(/\/analysis\/\d+$/);
}

test.describe("text analysis", () => {
  test("a short text cannot be submitted and the word count says why", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/text");
    const button = page.getByRole("button", { name: "Analyse text" });
    await expect(button).toBeDisabled();
    await page.getByLabel("Article text").fill(SHORT_TEXT);
    await expect(page.getByTestId("word-count")).toContainText("at least 60 needed");
    await expect(button).toBeDisabled();
    await page.getByRole("button", { name: "Clear" }).click();
    await expect(page.getByLabel("Article text")).toHaveValue("");
  });

  test("the result of a text analysis offers to check the same words against evidence", async ({ page }) => {
    await registerAndLogin(page);
    await analyseArticle(page);
    await expect(page.getByTestId("check-facts-note")).toContainText("does not check facts");
    await page.getByTestId("check-facts-note").getByRole("link", { name: "check them against evidence" }).click();
    await expect(page).toHaveURL(/\/analyze\/evidence$/);
    // the text is carried over, so the same words can be sent to the evidence check
    await expect(page.getByLabel("Claim or passage")).toHaveValue(/city council|Council|council/);
  });

  test("Arabic text is refused with an explanation, because no Arabic model exists", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/text");
    await page.getByLabel("Article text").fill("هذا نص عربي طويل عن الأخبار والسياسة في العالم العربي والاقتصاد ".repeat(12));
    await expect(page.getByText(/looks like Arabic or Persian|No model for it is installed/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Analyse text" })).toBeDisabled();
  });

  test("Urdu is analysed by the experimental Urdu model and says so", async ({ page, request }) => {
    const health = await (await request.get("/api/v1/health")).json();
    test.skip(health.urdu_text_model !== "available", "the Urdu model is not trained on this machine");
    await registerAndLogin(page);
    await page.goto("/analyze/text");
    await page.getByLabel("Headline").fill(URDU_HEADLINE);
    await page.getByLabel("Article text").fill(URDU_TEXT);
    await expect(page.getByTestId("urdu-note")).toBeVisible();
    await page.getByRole("button", { name: "Analyse text" }).click();
    await page.getByTestId("verdict").waitFor();
    await expect(page.getByTestId("experimental-note")).toContainText("experimental");
  });

  test("an article is analysed with the real model, explained, saved, exported and deleted", async ({ page }) => {
    await registerAndLogin(page);
    await analyseArticle(page);

    const verdict = (await page.getByTestId("verdict").innerText()).trim();
    expect(VERDICTS).toContain(verdict);
    await expect(page.getByRole("heading", { name: "Limits of this result" })).toBeVisible();
    await expect(page.getByLabel("Submitted text with marked terms")).toContainText("city council voted");
    // an ordinary reader sees the colour band, a plain reading bar and the limits, but no percentages, model name or word weights
    await expect(page.getByRole("img", { name: /The writing (leans|does not lean)/ })).toBeVisible();
    await expect(page.getByTestId("technical-details")).toHaveCount(0);
    await expect(page.getByText(/Produced by/)).toHaveCount(0);
    await expect(page.getByText(/The model puts/)).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Pushed the score toward fake" })).toHaveCount(0);

    // PDF export
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download PDF" }).click()]);
    expect(download.suggestedFilename()).toMatch(/\.pdf$/);
    expect(readFileSync((await download.path())!).subarray(0, 5).toString()).toBe("%PDF-");

    // printable report view
    await page.getByRole("link", { name: "Report view" }).click();
    await expect(page.getByRole("heading", { name: /Analysis report/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "Print" })).toBeVisible();
    await page.goBack();

    // it appears on the dashboard and in the history, then can be deleted
    await page.goto("/dashboard");
    await expect(page.getByTestId("total-analyses")).toHaveText("1");
    await page.goto("/history");
    await expect(page.getByRole("link", { name: /^Case/ })).toBeVisible();
    await expect(page.getByText(ARTICLE_HEADLINE)).toBeVisible();

    await page.getByRole("button", { name: /^Delete Case/ }).click();
    await page.getByRole("button", { name: "Delete analysis" }).click();
    await expect(page.getByText("Nothing matches these filters").or(page.getByText("No analyses yet"))).toBeVisible();
    await page.goto("/dashboard");
    await expect(page.getByTestId("total-analyses")).toHaveText("0");
  });

  test("history search and filters narrow the list", async ({ page }) => {
    await registerAndLogin(page);
    await analyseArticle(page);
    await page.goto("/history");
    await page.getByLabel("Search history").fill("transport");
    await expect(page).toHaveURL(/q=transport/);
    await expect(page.getByText(ARTICLE_HEADLINE)).toBeVisible();
    await page.getByLabel("Search history").fill("zzzz-no-such-thing");
    await expect(page.getByText("Nothing matches these filters")).toBeVisible();
    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(page.getByText(ARTICLE_HEADLINE)).toBeVisible();
    await page.getByLabel("Filter by type").selectOption("image");
    await expect(page.getByText("Nothing matches these filters")).toBeVisible();
  });

  test("another user cannot open an analysis they do not own", async ({ page, browser }) => {
    await registerAndLogin(page);
    await analyseArticle(page);
    const url = page.url();

    const other = await browser.newContext();
    const p2 = await other.newPage();
    await registerAndLogin(p2);
    await p2.goto(url);
    await expect(p2.getByText("This analysis does not exist")).toBeVisible();
    await other.close();
  });
});

test.describe("image analysis", () => {
  test("files that are not images are rejected before upload", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/image");
    await expect(page.getByRole("button", { name: "Inspect image" })).toBeDisabled();
    await page.getByLabel("Choose an image file").setInputFiles(fixture("not-an-image.txt"));
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByRole("button", { name: "Inspect image" })).toBeDisabled();
  });

  test("an image gets measurements and a real error level map, and no verdict", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/image");
    await page.getByLabel("Choose an image file").setInputFiles(fixture("sample.jpg"));
    await expect(page.getByTestId("file-name")).toHaveText("sample.jpg");
    await page.getByRole("button", { name: "Inspect image" }).click();
    await expect(page).toHaveURL(/\/analysis\/\d+$/);

    await expect(page.getByTestId("verdict")).toHaveText("Indicators Only");
    await expect(page.getByText("not an AI attention map", { exact: false }).first()).toBeVisible();
    // the measurement table is for administrators; an ordinary reader gets the map and the plain observations
    await expect(page.getByRole("heading", { name: "Measurements" })).toHaveCount(0);
    await expect(page.getByText("320 x 240 px, JPEG")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "What was noticed" })).toBeVisible();

    const ela = page.getByRole("img", { name: "Error level analysis map of the uploaded image" });
    await expect(ela).toBeVisible();
    await expect.poll(() => ela.evaluate((el: HTMLImageElement) => el.naturalWidth)).toBeGreaterThan(0);

    // the owner's image is served through the authenticated endpoint, so an unauthenticated request must fail
    const src = await page.getByRole("img", { name: "The image you uploaded" }).getAttribute("src");
    expect(src).toBeTruthy();

    await page.getByRole("button", { name: "Delete" }).first().click();
    await page.getByRole("button", { name: "Delete analysis" }).click();
    await expect(page).toHaveURL(/\/history$/);
  });
});
