export type Tone = "bad" | "ok" | "warn" | "info" | "neutral";

/** The API sends UTC. A timestamp with no offset ("2026-11-21T08:21:37") would be read by the browser as local time and
 * show the wrong hour, so one without an offset is treated as UTC. */
export function parseApiDate(iso: string): Date {
  const hasOffset = /(Z|[+-]\d{2}:?\d{2})$/i.test(iso);
  return new Date(hasOffset || !/T\d{2}:\d{2}/.test(iso) ? iso : `${iso}Z`);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = parseApiDate(iso);
  return Number.isNaN(d.getTime()) ? "-" : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function formatDay(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  return value === null || value === undefined ? "-" : `${(value * 100).toFixed(digits)}%`;
}

export function formatNumber(value: number): string {
  return value.toLocaleString();
}

export function caseNumber(id: number): string {
  return `Case ${String(id).padStart(4, "0")}`;
}

/** How a verdict is shown. Colour is never the only signal: every tone also has a label and an icon. */
export function verdictTone(verdict: string): Tone {
  switch (verdict) {
    case "Likely Fake": return "bad";
    case "Likely Real": return "ok";
    case "Supported": return "ok";
    case "Contradicted": return "bad";
    case "Mixed Evidence": return "warn";
    case "Insufficient Evidence": return "warn";
    case "Mismatch Flagged": return "warn";
    case "Unverified": return "warn";
    case "Indicators Only": return "info";
    default: return "neutral";
  }
}

export type Band = "real" | "fake" | "unsure" | "flag";

/** The colour band a verdict gets on a result: green, red, amber for a flag to look closer, and slate for "not sure". */
export function verdictBand(verdict: string): Band {
  switch (verdict) {
    case "Likely Real": case "Supported": return "real";
    case "Likely Fake": case "Contradicted": return "fake";
    case "Mismatch Flagged": return "flag";
    default: return "unsure";
  }
}

/** What each analysis type is called in lists, headings and reports. */
export const ANALYSIS_TYPE_LABEL: Record<string, string> = {
  text: "Text analysis", image: "Image inspection", url: "News URL analysis", video: "Video analysis", multimodal: "Multimodal analysis", evidence: "Evidence check",
};

export const MODULE_LABEL: Record<string, string> = {
  text: "Text", text_ur: "Text (Urdu)", image: "Image", video: "Video", multimodal: "Multimodal", evidence: "Evidence", url: "News URL",
};

export const STATUS_LABEL: Record<string, string> = {
  trained_baseline: "Trained baseline", pretrained: "Pretrained", heuristic: "Heuristic checks", experimental: "Experimental",
  unavailable: "Unavailable", planned: "Planned",
};

const DATASET_NAMES: Record<string, string> = { gonzaloa_fake_news: "GonzaloA fake news", liar2_test: "LIAR2" };
/** Readable name for a dataset identifier from the evaluation file; unknown identifiers are shown as they are. */
export function datasetLabel(id: string): string {
  return DATASET_NAMES[id] ?? id;
}

/**
 * Accuracy of giving the more common label every time, worked out from a confusion matrix. A classifier whose accuracy
 * is not above this has learned nothing a constant answer would not already give.
 */
export function majorityAccuracy(m: { tn: number; fp: number; fn: number; tp: number }): number {
  const total = m.tn + m.fp + m.fn + m.tp;
  return total === 0 ? 0 : Math.max(m.tn + m.fp, m.fn + m.tp) / total;
}
