import { expect, test } from "@playwright/test";
import { ARTICLE_HEADLINE, ARTICLE_TEXT } from "./fixtures/article";
import { login, loginAsAdmin, logout, newUser, PASSWORD, register, registerAndLogin, tokenOf } from "./helpers";

const ADMIN = { email: "admin@example.com", password: "AdminPass123" };

test.describe("administration", () => {
  test("ordinary users cannot reach the admin pages", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/admin");
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole("link", { name: "Users", exact: true })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Admin console" })).toHaveCount(0);
    // the technical pages, old address and new, are not for ordinary users
    for (const path of ["/admin/users", "/admin/models", "/admin/methodology", "/models", "/methodology"]) {
      await page.goto(path);
      await expect(page).toHaveURL(/\/dashboard$/);
    }
  });

  test("the server refuses the model registry and the evaluation to everyone but administrators", async ({ page, request }) => {
    await registerAndLogin(page);
    const token = await tokenOf(page);
    for (const path of ["/models", "/models/text/evaluation", "/models/video/evaluation", "/admin/stats", "/admin/models"]) {
      expect((await request.get(`/api/v1${path}`)).status(), `${path} without a token`).toBe(401);
      expect((await request.get(`/api/v1${path}`, { headers: { Authorization: `Bearer ${token}` } })).status(), `${path} as a user`).toBe(403);
    }
    // what a visitor needs is public, and carries nothing technical
    const pub = await request.get("/api/v1/modules");
    expect(pub.status()).toBe(200);
    expect(JSON.stringify(await pub.json())).not.toMatch(/roc|joblib|logistic|liar/i);
  });

  test("an administrator gets the console, the technical pages, and the technical details of a result", async ({ page, browser }) => {
    const ctx = await browser.newContext();
    const up = await ctx.newPage();
    await registerAndLogin(up);
    await up.goto("/analyze/text");
    await up.getByLabel("Headline").fill(ARTICLE_HEADLINE);
    await up.getByLabel("Article text").fill(ARTICLE_TEXT);
    await up.getByRole("button", { name: "Analyse text" }).click();
    await expect(up).toHaveURL(/\/analysis\/\d+$/);
    await ctx.close();

    await loginAsAdmin(page);
    await page.getByRole("link", { name: "Admin console" }).click();
    await expect(page).toHaveURL(/\/admin$/);
    const nav = page.getByRole("navigation", { name: "Main" });
    for (const label of ["Overview", "Users", "Models and measurements", "Methodology"]) await expect(nav.getByRole("link", { name: label })).toBeVisible();
    await nav.getByRole("link", { name: "Models and measurements" }).click();
    await expect(page.getByRole("heading", { name: "How the text model performs" })).toBeVisible();
    await expect(page.getByRole("cell", { name: /Logistic regression/ })).toBeVisible();
    await nav.getByRole("link", { name: "Methodology" }).click();
    await expect(page.getByRole("heading", { name: "Text analysis: testing" })).toBeVisible();
    await page.goto("/models");   // the old address leads to the console for an administrator
    await expect(page).toHaveURL(/\/admin\/models$/);
  });

  test("an administrator's own result carries a closed technical section that an ordinary user's does not", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/analyze/text");
    await page.getByLabel("Headline").fill(ARTICLE_HEADLINE);
    await page.getByLabel("Article text").fill(ARTICLE_TEXT);
    await page.getByRole("button", { name: "Analyse text" }).click();
    await expect(page).toHaveURL(/\/analysis\/\d+$/);
    const tech = page.getByTestId("technical-details");
    await expect(tech).toBeVisible();
    await tech.getByText("Technical details").click();
    await expect(tech.getByText(/The model puts/)).toBeVisible();
    await expect(tech.getByText(/Produced by/)).toContainText(/trained baseline/i);
    await expect(tech.getByRole("heading", { name: "Pushed the score toward fake" })).toBeVisible();
  });

  test("an administrator sees system totals, but not other people's analyses", async ({ page, browser }) => {
    // a normal user makes an analysis first
    const ctx = await browser.newContext();
    const up = await ctx.newPage();
    await registerAndLogin(up);
    await up.goto("/analyze/text");
    await up.getByLabel("Headline").fill(ARTICLE_HEADLINE);
    await up.getByLabel("Article text").fill(ARTICLE_TEXT);
    await up.getByRole("button", { name: "Analyse text" }).click();
    await expect(up).toHaveURL(/\/analysis\/\d+$/);
    const analysisUrl = up.url();
    await ctx.close();

    await login(page, ADMIN.email, ADMIN.password);
    await page.goto("/admin");
    await expect(page.getByRole("heading", { name: "Administration" })).toBeVisible();
    await expect(page.getByText("Registered users")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Audit log" })).toBeVisible();
    await expect(page.getByRole("cell", { name: /login/i }).first()).toBeVisible();

    await page.goto(analysisUrl);
    await expect(page.getByText("This analysis does not exist")).toBeVisible();
  });

  test("feedback is reviewed by an administrator and the user sees the new status", async ({ page, browser }) => {
    const ctx = await browser.newContext();
    const up = await ctx.newPage();
    const user = await registerAndLogin(up);
    await up.goto("/contact");
    const message = `The result on my article looked wrong ${Date.now()}`;
    await up.getByRole("textbox", { name: "Message" }).fill(message);
    await up.getByRole("button", { name: "Send feedback" }).click();
    await expect(up.getByText("Feedback sent.")).toBeVisible();

    await login(page, ADMIN.email, ADMIN.password);
    await page.goto("/admin");
    const item = page.getByRole("listitem").filter({ hasText: message });
    await expect(item).toBeVisible();
    await item.getByRole("button", { name: "Mark reviewed" }).click();
    await expect(page.getByText("Marked as reviewed.")).toBeVisible();

    await up.reload();
    await expect(up.getByText("Reviewed", { exact: true })).toBeVisible();
    void user;
    await ctx.close();
  });

  test("deactivating a user ends their access, and reactivating restores it", async ({ page, browser }) => {
    const victim = newUser();
    const ctx = await browser.newContext();
    const vp = await ctx.newPage();
    await register(vp, victim);
    await login(vp, victim.email);

    await login(page, ADMIN.email, ADMIN.password);
    await page.goto("/admin/users");
    await page.getByLabel("Search users").fill(victim.username);
    await expect(page.getByRole("row", { name: new RegExp(victim.username) })).toBeVisible();
    await page.getByRole("button", { name: `Deactivate ${victim.username}` }).click();
    await page.getByRole("button", { name: "Deactivate", exact: true }).click();
    await expect(page.getByText("User updated.")).toBeVisible();
    await expect(page.getByText("Deactivated")).toBeVisible();

    // their existing session stops working and a new login is refused
    await vp.goto("/dashboard");
    await expect(vp).toHaveURL(/\/login$/);
    await vp.getByLabel("E-mail or username").fill(victim.email);
    await vp.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await vp.getByRole("button", { name: "Log in" }).click();
    await expect(vp.getByRole("alert")).toBeVisible();

    // the first notice disappears after a few seconds; wait for that so the next "User updated." is unambiguous
    await expect(page.getByText("User updated.")).toHaveCount(0, { timeout: 10_000 });
    await page.getByRole("button", { name: `Reactivate ${victim.username}` }).click();
    await page.getByRole("button", { name: "Reactivate", exact: true }).click();
    await expect(page.getByText("User updated.")).toBeVisible();
    await expect(page.getByText("Deactivated")).toHaveCount(0);
    await login(vp, victim.email);
    await ctx.close();
  });

  test("an administrator cannot demote or deactivate themselves", async ({ page }) => {
    await login(page, ADMIN.email, ADMIN.password);
    await page.goto("/admin/users");
    await page.getByLabel("Search users").fill("admin@example.com");
    const row = page.getByRole("row", { name: /admin@example.com/ });
    await expect(row).toBeVisible();
    await expect(row.getByRole("button", { name: /Remove administrator rights/ })).toBeDisabled();
    await expect(row.getByRole("button", { name: /^Deactivate/ })).toBeDisabled();
    await logout(page);
  });
});
