import { expect, type Page } from "@playwright/test";

export const PASSWORD = "Sturdy-Pass-42";

let counter = 0;
export function newUser() {
  counter += 1;
  const id = `${Date.now().toString(36)}${counter}`;
  return { email: `user.${id}@example.com`, username: `user_${id}`, full_name: `Test User ${counter}`, password: PASSWORD };
}

export async function register(page: Page, user = newUser()) {
  await page.goto("/register");
  await page.getByLabel("E-mail address").fill(user.email);
  await page.getByLabel("Username").fill(user.username);
  await page.getByLabel("Full name").fill(user.full_name);
  await page.getByLabel("Password", { exact: true }).fill(user.password);
  await page.getByLabel("Confirm password").fill(user.password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/login$/);
  return user;
}

export async function login(page: Page, identifier: string, password = PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("E-mail or username").fill(identifier);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

export async function registerAndLogin(page: Page) {
  const user = await register(page);
  await login(page, user.email, user.password);
  return user;
}

export async function logout(page: Page) {
  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitem", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);
}

export const ADMIN = { email: "admin@example.com", password: "AdminPass123" };

export async function loginAsAdmin(page: Page) {
  await login(page, ADMIN.email, ADMIN.password);
}

/** The API token of a signed-in browser page, for calls that need an Authorization header. */
export async function tokenOf(page: Page): Promise<string> {
  return page.evaluate(() => sessionStorage.getItem("ddn.token") ?? localStorage.getItem("ddn.token") ?? "");
}
