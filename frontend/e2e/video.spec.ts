import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { loginAsAdmin, registerAndLogin } from "./helpers";

const NO_FACE = fileURLToPath(new URL("./fixtures/sample.webm", import.meta.url));
// The test backend treats the magenta corner of these frames as "a face is here" (see run_backend.py); everything after
// that, the frame classifier, the aggregation, the rules and the page, is the real code.
const WITH_FACE = fileURLToPath(new URL("./fixtures/face_stand_in.webm", import.meta.url));

// The video module needs OpenCV (scripts/setup/install_ml.sh). A clean install without it reports the module as
// "unavailable" and the Analyse button stays disabled, so the tests that analyse a video skip themselves there.
async function skipWithoutOpenCv(request: import("@playwright/test").APIRequestContext) {
  const models = await (await request.get("/api/v1/modules")).json();
  const status = models.models.find((m: { module: string }) => m.module === "video")?.status;
  test.skip(status === "unavailable", "OpenCV is not installed here (run scripts/setup/install_ml.sh)");
}

test.describe("video", () => {
  test("the page is a real form, not a placeholder", async ({ page }) => {
    await registerAndLogin(page);
    await page.goto("/analyze/video");
    await expect(page.getByRole("heading", { name: "Analyse a video", level: 1 })).toBeVisible();
    await expect(page.getByText("Not available in this build")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Analyse video" })).toBeDisabled();
    await page.getByLabel("Choose a video file").setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("hello") });
    await expect(page.getByTestId("video-error")).toContainText("Choose an MP4, MOV, WebM or AVI video");
  });

  test("a video with no usable face gets no verdict and says why", async ({ page, request }) => {
    await skipWithoutOpenCv(request);
    await registerAndLogin(page);
    await page.goto("/analyze/video");
    await page.getByLabel("Choose a video file").setInputFiles(NO_FACE);
    await expect(page.getByTestId("file-name")).toHaveText("sample.webm");
    await page.getByRole("button", { name: "Analyse video" }).click();
    await expect(page.getByTestId("verdict")).toHaveText("Unverified");
    await expect(page.getByText("A video is never judged from a single frame").first()).toBeVisible();
    const summary = page.getByTestId("video-summary");
    await expect(summary).toContainText("Too few frames with a face");
    await expect(summary).toContainText("0 (at least 8 are needed for a call)");
    await expect(page.getByTestId("frame-based-note")).toContainText("not a model that learns motion");
    await expect(page.getByTestId("frame-grid").getByText("no face").first()).toBeVisible();
  });

  test("frames, scores over time, the video, the report and deletion", async ({ page, request }) => {
    await skipWithoutOpenCv(request);
    await registerAndLogin(page);
    await page.goto("/analyze/video");
    await page.getByLabel("Choose a video file").setInputFiles(WITH_FACE);
    await page.getByRole("button", { name: "Analyse video" }).click();
    await page.getByTestId("verdict").waitFor({ timeout: 90_000 });

    const models = await (await request.get("/api/v1/modules")).json();
    const status = models.models.find((m: { module: string }) => m.module === "video").status;
    const verdict = await page.getByTestId("verdict").textContent();
    const summary = page.getByTestId("video-summary");
    await expect(summary).toContainText("evenly across the whole video");
    await expect(summary).not.toContainText("0 (at least 8");
    await expect(page.getByTestId("frame-based-note")).toContainText("not a model that learns motion");
    if (status === "experimental") {
      // the real classifier scored every frame the stand-in marked; whatever it says, the page must show the numbers behind it
      expect(["Likely Fake", "Likely Real", "Unverified"]).toContain(verdict);
      await expect(summary).toContainText("Video score");
      await expect(page.getByTestId("frame-chart").locator("circle.cursor-pointer").first()).toBeVisible();
    } else {
      // no classifier on this machine: measurements only, and the page says so instead of inventing scores
      await expect(page.getByTestId("verdict")).toHaveText("Indicators Only");
      await expect(page.getByTestId("frame-chart")).toBeVisible();
    }

    // thumbnails are real images fetched with the login token
    const thumbs = page.getByTestId("frame-grid").locator("img");
    await expect(thumbs.first()).toBeVisible();
    await expect.poll(async () => thumbs.first().evaluate((el: HTMLImageElement) => el.naturalWidth)).toBeGreaterThan(0);

    // the video is only downloaded when asked for, and then plays
    await expect(page.getByTestId("video-player")).toHaveCount(0);
    await page.getByRole("button", { name: /Load the video to play it/ }).click();
    const player = page.getByTestId("video-player");
    await expect(player).toBeVisible();
    await expect.poll(async () => player.evaluate((el: HTMLVideoElement) => el.readyState)).toBeGreaterThanOrEqual(1);
    expect(await player.evaluate((el: HTMLVideoElement) => el.duration)).toBeGreaterThan(5);

    const pdf = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download PDF" }).click()]);
    expect(pdf[0].suggestedFilename()).toMatch(/^analysis-\d+\.pdf$/);

    await page.goto("/history?analysis_type=video");
    await expect(page.getByRole("cell", { name: "face_stand_in.webm" })).toBeVisible();
    await page.getByRole("button", { name: /^Delete Case/ }).click();
    await page.getByRole("button", { name: "Delete analysis" }).click();
    await expect(page.getByText("Nothing matches these filters").or(page.getByText("No analyses yet"))).toBeVisible();
    await page.goto("/dashboard");
    await expect(page.getByTestId("total-analyses")).toHaveText("0");
  });

  test("the Models page shows the measured results and says what they do not show", async ({ page, request }) => {
    const models = await (await request.get("/api/v1/modules")).json();
    const status = models.models.find((m: { module: string }) => m.module === "video").status;
    await loginAsAdmin(page);
    await page.goto("/admin/models");
    await expect(page.getByRole("row").filter({ hasText: "Video" }).first()).toBeVisible();
    if (status !== "experimental") {
      await expect(page.getByTestId("video-eval-section")).toHaveCount(0); // nothing is shown that was not measured here
      return;
    }
    const section = page.getByTestId("video-eval-section");
    await expect(section).toContainText("frame-based");
    for (const key of ["calibration", "test", "fresh"]) await expect(page.getByTestId(`video-eval-${key}`)).toContainText(/0\.\d{3}/);
    await expect(section).toContainText("optimistic");
    await expect(section).toContainText("Audio is not analysed");
  });
});
