import { describe, expect, it } from "vitest";
import { formatBytes, validateImageFile } from "@/utils/files";
import { caseNumber, datasetLabel, formatPercent, majorityAccuracy, parseApiDate, verdictTone } from "@/utils/format";
import { highlightSegments } from "@/utils/highlight";
import { passwordIsValid, passwordRules } from "@/utils/password";
import { countWords, looksArabicScript, looksUrdu } from "@/utils/text";

describe("password rules", () => {
  it("mirror the server: 8+ characters, a letter and a digit", () => {
    expect(passwordIsValid("abc12345")).toBe(true);
    expect(passwordIsValid("short1")).toBe(false);
    expect(passwordIsValid("lettersonly")).toBe(false);
    expect(passwordIsValid("12345678")).toBe(false);
  });
  it("count bytes, not characters, for the 72 byte limit", () => {
    const ok = "a1" + "é".repeat(30); // 62 bytes
    const tooLong = "a1" + "é".repeat(40); // 82 bytes
    expect(passwordIsValid(ok)).toBe(true);
    expect(passwordRules(tooLong).find((r) => r.id === "bytes")?.ok).toBe(false);
  });
});

describe("text helpers", () => {
  it("counts words", () => {
    expect(countWords("")).toBe(0);
    expect(countWords("  one   two\nthree ")).toBe(3);
  });
  it("detects Arabic-script text but not English or mixed English", () => {
    expect(looksArabicScript("یہ ایک اردو خبر ہے جو بہت اہم ہے")).toBe(true);
    expect(looksArabicScript("The council met on Tuesday.")).toBe(false);
    expect(looksArabicScript("Mostly English text with a single word خبر inside it for the test")).toBe(false);
    expect(looksArabicScript("12345 !!!")).toBe(false);
  });
});

describe("image file validation", () => {
  const file = (name: string, type: string, size: number) => new File([new Uint8Array(size)], name, { type });
  it("accepts JPEG, PNG and WEBP", () => {
    for (const [n, t] of [["a.jpg", "image/jpeg"], ["a.png", "image/png"], ["a.webp", "image/webp"]]) expect(validateImageFile(file(n, t, 10), 10)).toBeNull();
  });
  it("rejects other types, empty files and oversize files", () => {
    expect(validateImageFile(file("a.gif", "image/gif", 10), 10)).toMatch(/JPEG, PNG or WEBP/);
    expect(validateImageFile(file("a.txt", "text/plain", 10), 10)).toMatch(/JPEG, PNG or WEBP/);
    expect(validateImageFile(file("a.jpg", "image/jpeg", 0), 10)).toMatch(/empty/);
    expect(validateImageFile(file("a.jpg", "image/jpeg", 3 * 1024 * 1024), 2)).toMatch(/limit is 2 MB/);
  });
  it("formats sizes", () => {
    expect(formatBytes(500)).toBe("500 B");
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});

describe("formatting", () => {
  it("formats percentages, case numbers and dataset names", () => {
    expect(formatPercent(0.9731, 1)).toBe("97.3%");
    expect(formatPercent(null)).toBe("-");
    expect(caseNumber(7)).toBe("Case 0007");
    expect(datasetLabel("liar2_test")).toBe("LIAR2");
    expect(datasetLabel("something_else")).toBe("something_else");
  });
  it("gives every verdict its own tone, so meaning is not left to chance", () => {
    expect([verdictTone("Likely Fake"), verdictTone("Likely Real"), verdictTone("Unverified"), verdictTone("Indicators Only")]).toEqual(["bad", "ok", "warn", "info"]);
  });
});

describe("highlightSegments", () => {
  const fake = [{ term: "city council", weight: 0.5 }];
  const real = [{ term: "tuesday", weight: -0.4 }];
  it("marks every word of a listed term and reproduces the original text exactly", () => {
    const text = "The City Council met on Tuesday, said the mayor.";
    const segs = highlightSegments(text, fake, real);
    expect(segs.map((s) => s.text).join("")).toBe(text);
    expect(segs.filter((s) => s.tone === "fake").map((s) => s.text)).toEqual(["City", "Council"]);
    expect(segs.filter((s) => s.tone === "real").map((s) => s.text)).toEqual(["Tuesday"]);
  });
  it("lets the heavier weight win when a word is in both lists", () => {
    const segs = highlightSegments("budget", [{ term: "budget", weight: 0.1 }], [{ term: "budget", weight: -0.9 }]);
    expect(segs).toEqual([{ text: "budget", tone: "real" }]);
  });
  it("marks nothing when there are no terms", () => {
    expect(highlightSegments("Plain text.", [], [])).toEqual([{ text: "Plain text.", tone: null }]);
  });
});

describe("parseApiDate", () => {
  it("reads a timestamp without an offset as UTC, not local time", () => {
    expect(parseApiDate("2026-11-21T08:21:37.707174").toISOString()).toBe("2026-11-21T08:21:37.707Z");
  });
  it("keeps an explicit offset", () => {
    expect(parseApiDate("2026-11-21T08:21:37Z").toISOString()).toBe("2026-11-21T08:21:37.000Z");
    expect(parseApiDate("2026-11-21T13:21:37+05:00").toISOString()).toBe("2026-11-21T08:21:37.000Z");
  });
  it("leaves a plain date alone", () => {
    expect(Number.isNaN(parseApiDate("2026-11-21").getTime())).toBe(false);
  });
});

describe("majorityAccuracy", () => {
  it("is the share of the more common label, so a constant answer has a score to beat", () => {
    // LIAR2 as measured: 973 true-ish and 1323 fake-ish statements, 2296 in all.
    expect(majorityAccuracy({ tn: 342, fp: 631, fn: 397, tp: 926 })).toBeCloseTo(1323 / 2296, 6);
    expect(majorityAccuracy({ tn: 5, fp: 0, fn: 5, tp: 0 })).toBe(0.5);
    expect(majorityAccuracy({ tn: 0, fp: 0, fn: 0, tp: 0 })).toBe(0);
  });
});

describe("looksUrdu", () => {
  it("tells Urdu from Arabic, Persian and English by the letters only Urdu uses", () => {
    expect(looksUrdu("یہ ایک اردو خبر ہے جو بہت اہم ہے")).toBe(true);
    expect(looksUrdu("هذا نص عربي طويل عن الأخبار والسياسة في العالم العربي")).toBe(false);
    expect(looksUrdu("این یک متن فارسی درباره اخبار و سیاست است")).toBe(false);
    expect(looksUrdu("The council met on Tuesday.")).toBe(false);
    expect(looksUrdu("")).toBe(false);
  });
});
