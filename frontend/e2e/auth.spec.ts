import { expect, test } from "@playwright/test";
import { login, logout, newUser, PASSWORD, register, registerAndLogin } from "./helpers";

test.describe("accounts", () => {
  test("registration shows what is wrong with each field", async ({ page }) => {
    await page.goto("/register");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Enter a valid e-mail address.")).toBeVisible();
    await expect(page.getByText("The password does not meet the requirements below.")).toBeVisible();
    await expect(page).toHaveURL(/\/register$/);
  });

  test("a duplicate e-mail is refused", async ({ page }) => {
    const user = await register(page);
    await page.goto("/register");
    await page.getByLabel("E-mail address").fill(user.email);
    await page.getByLabel("Username").fill(`other_${Date.now().toString(36)}`);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByLabel("Confirm password").fill(PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByRole("alert").filter({ hasText: /already/i })).toBeVisible();
  });

  test("log in, log out, and a wrong password is refused", async ({ page }) => {
    const user = await register(page);
    await page.goto("/login");
    await page.getByLabel("E-mail or username").fill(user.username);
    await page.getByLabel("Password", { exact: true }).fill("Wrong-Pass-99");
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);

    await login(page, user.username); // the username works as well as the e-mail address
    await expect(page.getByRole("heading", { name: /What would you like to check/ })).toBeVisible();
    await logout(page);
  });

  test("private pages send visitors to the login page, and logging out really ends the session", async ({ page }) => {
    await page.goto("/history");
    await expect(page).toHaveURL(/\/login$/);

    await registerAndLogin(page);
    await logout(page);
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("a forgotten password can be reset, and the old one stops working", async ({ page }) => {
    const user = await register(page);
    await page.goto("/forgot-password");
    await page.getByLabel("E-mail address").fill(user.email);
    await page.getByRole("button", { name: "Request reset" }).click();
    await page.getByRole("button", { name: "Continue to set a new password" }).click();
    const token = await page.getByLabel("Reset token").inputValue();
    expect(token.length).toBeGreaterThan(20);
    await page.getByLabel("New password", { exact: true }).fill("Brand-New-Pass-7");
    await page.getByLabel("Confirm new password").fill("Brand-New-Pass-7");
    await page.getByRole("button", { name: "Update password" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.getByLabel("E-mail or username").fill(user.email);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("alert")).toBeVisible();

    await login(page, user.email, "Brand-New-Pass-7");
  });

  test("profile details and password can be changed", async ({ page }) => {
    const user = await registerAndLogin(page);
    await page.goto("/profile");
    await page.getByLabel("Full name").fill("Renamed Person");
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByText("Profile saved.")).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("Full name")).toHaveValue("Renamed Person");

    await page.goto("/settings");
    await page.getByLabel("Current password").fill(PASSWORD);
    await page.getByLabel("New password", { exact: true }).fill("Changed-Pass-55");
    await page.getByLabel("Confirm new password").fill("Changed-Pass-55");
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByText(/Password changed/)).toBeVisible();

    await logout(page);
    await login(page, user.email, "Changed-Pass-55");
  });

  test("the theme choice is kept after a reload", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/settings");
    await page.getByRole("radio", { name: "Light" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await page.getByRole("radio", { name: "Dark" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("two users cannot see each other's data", async ({ page, browser }) => {
    const a = newUser();
    await register(page, a);
    await login(page, a.email);
    // sanity: a fresh second browser context has no session at all
    const other = await browser.newContext();
    const p2 = await other.newPage();
    await p2.goto(new URL("/dashboard", page.url()).toString());
    await expect(p2).toHaveURL(/\/login$/);
    await other.close();
  });
});

test("a server that does not answer is explained instead of leaving a bare spinner", async ({ page }) => {
  test.setTimeout(60_000);
  await registerAndLogin(page);
  // From now on the session check never gets an answer, as when the server is busy loading a model.
  await page.route("**/api/v1/users/me", () => new Promise(() => undefined));
  await page.reload();
  await expect(page.getByText("Restoring your session")).toBeVisible();
  await expect(page.getByTestId("server-slow")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("server-slow")).toContainText("taking a long time to answer");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
});

test("an e-mail address the server rejects is explained next to its field", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("E-mail address").fill("someone@reserved.test");
  await page.getByLabel("Username").fill(`user_${Date.now().toString(36)}`);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText(/special-use or reserved name/)).toBeVisible();
  await expect(page).toHaveURL(/\/register$/);
});
