import { expect, test } from "@playwright/test";
import { registerAndLogin } from "./helpers";

// Real server, real inference model. Only the Wikipedia answer is canned (see run_backend.py), so no internet is needed.
const WRONG = "Jackie (2016 film) was directed by Peter Jackson.";
const RIGHT = "Jackie is a 2016 film directed by Pablo Larraín.";

test.describe("evidence check", () => {
  test("the page is a real form, not a placeholder", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/evidence");
    await expect(page.getByRole("heading", { name: "Check a claim against evidence", level: 1 })).toBeVisible();
    await expect(page.getByText("Not available in this build")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Check against evidence" })).toBeDisabled();
  });

  test("a wrong claim is contradicted by the evidence and every source is shown", async ({ page, request }) => {
    const health = await (await request.get("/api/v1/modules")).json();
    test.skip(health.models.find((m: { module: string }) => m.module === "evidence")?.status !== "pretrained", "the inference packages are not installed here");
    await registerAndLogin(page);
    await page.goto("/analyze/evidence");
    await page.getByLabel("Claim or passage").fill(WRONG);
    await page.getByRole("button", { name: "Check against evidence" }).click();
    await page.getByTestId("verdict").waitFor();
    await expect(page.getByTestId("verdict")).toHaveText("Contradicted");
    const card = page.getByTestId("evidence-claim");
    await expect(card).toContainText("Contradicts the claim");
    await expect(card).toContainText("Closest sentence");
    await expect(card).toContainText("Pablo Larraín");
    // the source that was not searched says why, instead of silently disappearing
    await expect(card.getByTestId("provider-status").filter({ hasText: "Google Fact Check" })).toContainText("not searched");
    await expect(page.getByText(/does not mean the claim is false|Insufficient/).first()).toBeVisible();

    await page.goto("/analyze/evidence");
    await page.getByLabel("Claim or passage").fill(RIGHT);
    await page.getByRole("button", { name: "Check against evidence" }).click();
    await expect(page.getByTestId("verdict")).toHaveText("Supported");
    await page.goto("/dashboard");
    await expect(page.getByTestId("total-evidence")).toHaveText("2");
  });

  test("a claim nothing is known about gets Insufficient Evidence, and text with no claim is refused", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/evidence");
    await page.getByLabel("Claim or passage").fill("I think we should all relax and enjoy the weather today everyone, really. ".repeat(6));
    await page.getByRole("button", { name: "Check against evidence" }).click();
    await expect(page.getByTestId("evidence-error")).toContainText("No checkable factual statement");
  });
});
