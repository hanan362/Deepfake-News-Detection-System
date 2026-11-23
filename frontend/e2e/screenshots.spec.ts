import { fileURLToPath } from "node:url";
import { test } from "@playwright/test";
import { ARTICLE_HEADLINE, ARTICLE_TEXT } from "./fixtures/article";
import { loginAsAdmin, registerAndLogin } from "./helpers";

// Not part of the normal run. `SCREENSHOTS=1 npx playwright test e2e/screenshots.spec.ts` writes pictures of the real
// interface to docs/screenshots, which the user manual uses.
test.skip(!process.env.SCREENSHOTS, "screenshot run only");
const out = (name: string) => fileURLToPath(new URL(`../../docs/screenshots/${name}.png`, import.meta.url));
const sample = fileURLToPath(new URL("./fixtures/sample.jpg", import.meta.url));

test("capture", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1360, height: 860 });

  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  await page.getByRole("form", { name: "Start a check" }).waitFor();
  await page.waitForTimeout(600);
  await page.screenshot({ path: out("01-landing"), fullPage: true });
  await page.goto("/login");
  await page.getByRole("button", { name: "Log in" }).waitFor();
  await page.screenshot({ path: out("02-login") });

  await registerAndLogin(page);
  await page.goto("/analyze/text");
  await page.getByLabel("Headline").fill(ARTICLE_HEADLINE);
  await page.getByLabel("Article text").fill(ARTICLE_TEXT);
  await page.screenshot({ path: out("04-text-analysis") });
  await page.getByRole("button", { name: "Analyse text" }).click();
  await page.getByTestId("verdict").waitFor();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: out("05-text-result"), fullPage: true });

  await page.goto("/analyze/image");
  await page.getByLabel("Choose an image file").setInputFiles(sample);
  await page.getByRole("button", { name: "Inspect image" }).click();
  await page.getByTestId("verdict").waitFor();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: out("06-image-result"), fullPage: true });

  await page.goto("/dashboard");
  await page.getByTestId("total-analyses").waitFor();
  await page.waitForTimeout(600);
  await page.screenshot({ path: out("07-dashboard"), fullPage: true });
  await page.goto("/history");
  await page.getByRole("table").waitFor();
  await page.screenshot({ path: out("08-history") });
  await page.goto("/analyze/video");
  await page.getByRole("heading", { level: 1 }).waitFor();
  await page.screenshot({ path: out("09-video-module") });

  // The same page in the dark theme, which follows the system setting by default.
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/dashboard");
  await page.getByTestId("total-analyses").waitFor();
  await page.waitForTimeout(500);
  await page.screenshot({ path: out("10-dashboard-dark"), fullPage: true });
  await page.emulateMedia({ colorScheme: "light" });

  await page.setViewportSize({ width: 390, height: 820 });
  await page.goto("/analyze/text");
  await page.getByLabel("Article text").waitFor();
  await page.screenshot({ path: out("11-mobile-text") });
  await page.goto("/analysis/1");
  await page.getByTestId("verdict").waitFor();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: out("12-mobile-result"), fullPage: true });

  // The administrator console: the pages and the result details that ordinary users never see.
  await page.setViewportSize({ width: 1360, height: 860 });
  await page.context().clearCookies();
  await page.evaluate(() => { sessionStorage.clear(); localStorage.removeItem("ddn.token"); });
  await loginAsAdmin(page);
  await page.goto("/admin");
  await page.getByRole("heading", { name: "Administration" }).waitFor();
  await page.waitForTimeout(900);
  await page.screenshot({ path: out("13-admin-overview"), fullPage: true });
  await page.goto("/admin/users");
  await page.getByRole("heading", { level: 1 }).waitFor();
  await page.waitForTimeout(600);
  await page.screenshot({ path: out("14-admin-users") });
  await page.goto("/admin/models");
  await page.getByRole("heading", { name: "Four classifiers, same data" }).waitFor();
  await page.screenshot({ path: out("03-models"), fullPage: true });
});
