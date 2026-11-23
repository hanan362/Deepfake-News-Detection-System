import { expect, test } from "@playwright/test";
import { registerAndLogin } from "./helpers";

// These tests run against the real server, the real models and the real address checks. A stand-in news site (see
// run_backend.py) answers for fictional host names, so no test needs the internet.
const ARTICLE_URL = "http://news.example/ferry-terminal";

test.describe("news address analysis", () => {
  test("the page offers a real form and says what it cannot do", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/url");
    await expect(page.getByRole("heading", { name: "Analyse a news address", level: 1 })).toBeVisible();
    await expect(page.getByText("Not available in this build")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Read and analyse" })).toBeDisabled();
    await page.getByLabel("Article address").fill("news.example/ferry-terminal");
    await expect(page.getByText("Start the address with http:// or https://")).toBeVisible();
    await expect(page.getByRole("button", { name: "Read and analyse" })).toBeDisabled();
    await page.getByLabel("Article address").fill("ftp://news.example/file");
    await expect(page.getByText("Start the address with http:// or https://")).toBeVisible();
    await expect(page.getByText(/never "fake"|never “fake”/).first()).toBeVisible();
  });

  test("an article is read, analysed, described by its website, exported and deleted", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/url");
    await page.getByLabel("Article address").fill(ARTICLE_URL);
    await page.getByRole("button", { name: "Read and analyse" }).click();
    await page.getByTestId("verdict").waitFor();
    await expect(page).toHaveURL(/\/analysis\/\d+$/);

    // the text result and the website result are separate, and the unfamiliar site is not called fake
    await expect(page.getByTestId("source-url")).toHaveText(ARTICLE_URL);
    const outcome = page.getByTestId("source-outcome");
    await expect(outcome).toHaveAttribute("data-assessment", "unknown");
    await expect(outcome).toContainText("Not enough information");
    await expect(outcome).not.toContainText(/\bfake\b/i);
    await expect(page.getByText("What was not checked")).toBeVisible();
    // how the text was obtained is shown, with the declared details
    await expect(page.getByTestId("extraction-note")).toContainText("words were read from");
    await expect(page.getByTestId("extraction-note")).toContainText("A. Reporter");
    // the extracted text is displayed so the reader can check it, without the page's menu or footer
    const shown = page.getByLabel("Submitted text with marked terms");
    await expect(shown).toContainText("harbour authority announced");
    await expect(shown).not.toContainText("Copyright notice");

    const pdf = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download PDF" }).click()]);
    expect(pdf[0].suggestedFilename()).toMatch(/^analysis-\d+\.pdf$/);

    await page.goto("/history?analysis_type=url");
    await expect(page.getByRole("row").filter({ hasText: "New ferry terminal to open in March" })).toBeVisible();
    await page.goto("/dashboard");
    await expect(page.getByTestId("total-url")).toHaveText("1");

    await page.goto("/history");
    await page.getByRole("button", { name: /^Delete Case/ }).click();
    await page.getByRole("button", { name: "Delete analysis" }).click();
    await expect(page.getByText("No analyses yet")).toBeVisible();
  });

  test("a recognised publisher is named and a satire site gets no verdict", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/url");
    await page.getByLabel("Article address").fill("http://www.reuters.com/ferry-terminal");
    await page.getByRole("button", { name: "Read and analyse" }).click();
    await expect(page.getByTestId("source-outcome")).toHaveAttribute("data-assessment", "recognised_publisher");
    await expect(page.getByTestId("source-outcome")).toContainText("says nothing about whether this particular article is accurate");

    await page.goto("/analyze/url");
    await page.getByLabel("Article address").fill("http://www.theonion.com/ferry-terminal");
    await page.getByRole("button", { name: "Read and analyse" }).click();
    await expect(page.getByTestId("verdict")).toHaveText("Unverified");
    await expect(page.getByTestId("source-outcome")).toHaveAttribute("data-assessment", "declared_satire");
  });

  test("a page that cannot be read says so and offers no verdict", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/url");
    await page.getByLabel("Article address").fill("http://news.example/js-only");
    await page.getByRole("button", { name: "Read and analyse" }).click();
    await expect(page.getByTestId("verdict")).toHaveText("Unverified");
    await expect(page.getByText(/Paste the text instead/).first()).toBeVisible();
  });

  for (const [label, address, message] of [
    ["the server's own address", "http://127.0.0.1/api/v1/health", /not an IP address/],
    ["an internal service port", "http://news.example:6379/", /standard web ports/],
    ["a host that resolves to a private network", "http://internal.example/admin", /private or internal network/],
    ["a file that is not a page", "http://news.example/report.pdf", /not a web page/],
  ] as const) {
    test(`refuses ${label} with an explanation`, async ({ page }) => {
      await registerAndLogin(page);
      await page.goto("/analyze/url");
      await page.getByLabel("Article address").fill(address);
      await page.getByRole("button", { name: "Read and analyse" }).click();
      await expect(page.getByTestId("url-error")).toContainText(message);
      await expect(page).toHaveURL(/\/analyze\/url$/);
    });
  }
});
