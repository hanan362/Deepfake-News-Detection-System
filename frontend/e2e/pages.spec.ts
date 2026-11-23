import { expect, test } from "@playwright/test";
import { registerAndLogin } from "./helpers";

test.describe("public pages", () => {
  test("the home page offers the check, shows what an answer looks like, and keeps the technical numbers out of sight", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Check a story before you share it");
    await expect(page.getByRole("form", { name: "Start a check" })).toBeVisible();
    for (const word of ["Likely Real", "Unverified", "Likely Fake"]) await expect(page.getByText(word, { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "What it cannot do" })).toBeVisible();
    // none of the measured numbers or model names is shown to a visitor
    for (const hidden of ["ROC AUC", "accuracy", "Logistic", "LIAR", "Methodology"]) await expect(page.getByText(hidden, { exact: false })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Models" })).toHaveCount(0);
    await page.getByRole("link", { name: "Create account" }).first().click();
    await expect(page).toHaveURL(/\/register$/);
  });

  test("text typed on the home page is waiting on the check page after signing in", async ({ page }) => {
    const text = "The harbour authority said on Monday that the new ferry terminal will open in March after two years of building work.";
    await page.goto("/");
    await page.getByRole("textbox", { name: "Paste the article" }).fill(text);
    await page.getByRole("button", { name: "Sign in and check" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await registerAndLogin(page);
    await page.goto("/");
    await page.getByRole("textbox", { name: "Paste the article" }).fill(text);
    await page.getByRole("button", { name: "Check it" }).click();
    await expect(page).toHaveURL(/\/analyze\/text$/);
    await expect(page.getByLabel("Article text")).toHaveValue(text);
  });

  test("the about page loads, and the technical pages are not in the public site", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByRole("heading", { name: "About the project" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "How to read an answer" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "The team" })).toBeVisible();
    await expect(page.getByText("Mudassar Hussain")).toBeVisible();   // the names the team supplied
    await expect(page.getByText("Mr. Talha Jahangir")).toBeVisible();
    await expect(page.getByText("Muhammad Nawaz Sharif University of Engineering and Technology, Multan").first()).toBeVisible();
    await expect(page.getByText("Built with")).toHaveCount(0);   // the technology list is on the administrators' methodology page
    // a visitor who asks for a technical page is sent to sign in, not shown it
    await page.goto("/models");
    await expect(page).toHaveURL(/\/login$/);
    await page.goto("/methodology");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("an unknown address shows the 404 page", async ({ page }) => {
    await page.goto("/definitely/not/a/page");
    await expect(page.getByRole("heading", { name: "There is nothing at this address" })).toBeVisible();
    await page.getByRole("link", { name: "Go to the home page" }).click();
    await expect(page).toHaveURL(/\/$/);
  });

  test("the server answers an unknown API path in the standard error shape", async ({ request }) => {
    const res = await request.get("/api/v1/nope");
    expect(res.status()).toBe(404);
    expect((await res.json()).error.code).toBeTruthy();
  });
});

test.describe("signed-in navigation", () => {
  test("every sidebar destination loads without console errors", async ({ page }) => {
    const problems: string[] = [];
    page.on("pageerror", (e) => problems.push(e.message));
    page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
    await registerAndLogin(page);

    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav.getByRole("link", { name: "Home" })).toBeVisible();
    for (const technical of ["Models", "Methodology", "Model information"]) await expect(nav.getByRole("link", { name: technical })).toHaveCount(0);
    const hrefs = await nav.getByRole("link").evaluateAll((els) => els.map((e) => (e as HTMLAnchorElement).getAttribute("href")!));
    expect(hrefs.length).toBeGreaterThanOrEqual(10);
    for (const href of hrefs) {
      await page.goto(href);
      await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      await expect(page.getByText("The page may have moved")).toHaveCount(0);
    }
    await page.goto("/contact");
    await expect(page.getByRole("heading", { name: "Contact and feedback" })).toBeVisible();
    expect(problems).toEqual([]);
  });

  test("feedback can be sent and is listed with its status", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/contact?category=feature_request&about=Video%20analysis");
    await expect(page.getByLabel("What is this about?")).toHaveValue("feature_request");
    const box = page.getByRole("textbox", { name: "Message" });
    await expect(box).toHaveValue(/^About: Video analysis/);
    await box.fill("About: Video analysis\n\nWe need video support for the demo.");
    await page.getByRole("button", { name: "Send feedback" }).click();
    await expect(page.getByText("Feedback sent.")).toBeVisible();
    await expect(page.getByText("We need video support for the demo.")).toBeVisible();
    await expect(page.getByText("Waiting for review")).toBeVisible();
  });
});
