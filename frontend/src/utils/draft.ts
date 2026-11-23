/**
 * The text a visitor typed on the home page before signing in. It is kept for the one tab, picked up once by the page
 * that runs the check, and then forgotten. It never leaves the browser until the person presses the check button.
 */
const KEY = "ddn.draft";
export type DraftKind = "text" | "url";

export function saveDraft(kind: DraftKind, value: string) {
  try { sessionStorage.setItem(KEY, JSON.stringify({ kind, value })); } catch { /* storage can be off; the person just types again */ }
}

export function takeDraft(kind: DraftKind): string {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return "";
    const d = JSON.parse(raw) as { kind?: string; value?: string };
    if (d.kind !== kind) return "";
    sessionStorage.removeItem(KEY);
    return typeof d.value === "string" ? d.value : "";
  } catch { return ""; }
}
