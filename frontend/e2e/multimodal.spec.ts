import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { ARTICLE_HEADLINE, ARTICLE_TEXT } from "./fixtures/article";
import { registerAndLogin } from "./helpers";

const SAMPLE = fileURLToPath(new URL("./fixtures/sample.jpg", import.meta.url));

// Real server, real text model, real image forensics and the real CLIP model where it is installed.
test.describe("image with text", () => {
  test("the page is a real form and needs at least one input", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/multimodal");
    await expect(page.getByRole("heading", { name: "Analyse an image with its text", level: 1 })).toBeVisible();
    await expect(page.getByText("Not available in this build")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Analyse together" })).toBeDisabled();
    await page.getByLabel("Headline or caption").fill("A caption");
    await expect(page.getByRole("button", { name: "Analyse together" })).toBeEnabled();
  });

  test("an image and an article give separate results, the match check and the rule that combines them", async ({ page, request }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/multimodal");
    await page.getByLabel("Choose an image file").setInputFiles(SAMPLE);
    await expect(page.getByTestId("file-name")).toHaveText("sample.jpg");
    await page.getByLabel("Headline or caption").fill(ARTICLE_HEADLINE);
    await page.getByLabel("Article text").fill(ARTICLE_TEXT);
    await page.getByRole("button", { name: "Analyse together" }).click();
    await page.getByTestId("verdict").waitFor();

    const fusion = page.getByTestId("fusion-panel");
    await expect(fusion).toContainText("Analysed");
    await expect(fusion).toContainText("fixed rule written by the project team");
    await expect(page.getByTestId("consistency-panel")).toBeVisible();
    // each modality keeps its own result: the text explanation and the image measurements
    await expect(page.getByRole("heading", { name: "What moved the score" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Measurements" })).toHaveCount(0);   // administrators only
    await expect(page.getByLabel("Submitted text with marked terms")).toContainText("city council");

    const models = await (await request.get("/api/v1/modules")).json();
    const status = models.models.find((m: { module: string }) => m.module === "multimodal").status;
    if (status === "pretrained") await expect(page.getByTestId("consistency-panel")).toHaveAttribute("data-label", /consistent|unclear|inconsistent/);

    const pdf = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download PDF" }).click()]);
    expect(pdf[0].suggestedFilename()).toMatch(/^analysis-\d+\.pdf$/);
    await page.goto("/history?analysis_type=multimodal");
    await expect(page.getByRole("row").filter({ hasText: "Multimodal" })).toBeVisible();
  });

  test("an image alone gets indicators only, and a short caption alone is not judged and cannot be compared", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/multimodal");
    await page.getByLabel("Choose an image file").setInputFiles(SAMPLE);
    await page.getByRole("button", { name: "Analyse together" }).click();
    await expect(page.getByTestId("verdict")).toHaveText("Indicators Only");
    await expect(page.getByTestId("fusion-panel")).toContainText("Not given");

    await page.goto("/analyze/multimodal");
    await page.getByLabel("Headline or caption").fill("A gradient photo");
    await page.getByRole("button", { name: "Analyse together" }).click();
    await expect(page.getByTestId("verdict")).toHaveText("Unverified");
    await expect(page.getByTestId("fusion-panel")).toContainText("Not possible");
  });

  test("a file that is not an image is refused with an explanation", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/multimodal");
    await page.getByLabel("Choose an image file").setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("hello") });
    await expect(page.getByTestId("multimodal-error")).toContainText("Choose a JPEG, PNG or WEBP image");
  });
});
