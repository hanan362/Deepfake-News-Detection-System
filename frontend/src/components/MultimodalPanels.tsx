import clsx from "clsx";
import type { ConsistencyResult, MultimodalDetails } from "@/types/api";

const MODALITY_TEXT: Record<string, string> = {
  analysed: "Analysed", not_provided: "Not given", too_short: "Given, but too short for the text model", unsupported_language: "Given, but in a language the models do not cover",
  assessed: "Checked", not_assessed: "Not checked (model unavailable)", not_possible: "Not possible (needs both an image and text)", declined: "Given, but not judged",
};

/** What was given, what each part produced, and the exact rule that turned them into one verdict. */
export function FusionPanel({ modalities, fusion }: { modalities: MultimodalDetails["modalities"]; fusion: MultimodalDetails["fusion"] }) {
  const rows: [string, string][] = [["Text", modalities.text], ["Image", modalities.image], ["Image and text match", modalities.consistency]];
  return (
    <div data-testid="fusion-panel">
      <dl className="divide-y divide-line rounded-panel border border-line text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-6 px-4 py-2.5"><dt className="text-ink-2">{k}</dt><dd className="text-right">{MODALITY_TEXT[v] ?? v}</dd></div>
        ))}
      </dl>
      <p className="mt-4 max-w-prose text-sm text-ink-2"><span className="font-medium text-ink">The rule.</span> {fusion.rule}</p>
      {fusion.notes.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-2 marker:text-ink-3">{fusion.notes.map((n) => <li key={n}>{n}</li>)}</ul>}
      <p className="mt-2 text-xs text-ink-3">This is a fixed rule written by the project team, not a learned model.</p>
    </div>
  );
}

const LABEL_TEXT: Record<string, string> = {
  consistent: "They appear to match", inconsistent: "They appear not to match", unclear: "Unclear", not_calibrated: "Similarity measured, not interpreted",
};
const LABEL_STYLE: Record<string, string> = { consistent: "border-ok/40 bg-ok/5", inconsistent: "border-warn/50 bg-warn/5", unclear: "border-line bg-panel", not_calibrated: "border-line bg-panel" };

/** The CLIP image-text similarity, the thresholds that turn it into a label, and where those thresholds came from. */
export function ConsistencyPanel({ c }: { c: ConsistencyResult }) {
  if (c.status !== "assessed" || c.similarity === null) {
    return <p className="rounded-panel border border-line p-4 text-sm text-ink-2" data-testid="consistency-panel">{c.note}</p>;
  }
  const label = c.label ?? "unclear";
  const t = c.thresholds;
  // the bar spans 0 to 0.5 cosine similarity, where nearly all image-caption pairs fall
  const pos = (v: number) => `${Math.min(100, Math.max(0, (v / 0.5) * 100))}%`;
  return (
    <div data-testid="consistency-panel" data-label={label}>
      <div className={clsx("rounded-panel border p-5", LABEL_STYLE[label])}>
        <p className="font-display text-2xl font-medium leading-tight">{LABEL_TEXT[label]}</p>
        <p className="mt-2 text-sm text-ink-2">Compared with the {c.caption_source}: <span className="text-ink">“{c.caption_used}”</span></p>
        {t && (
          <div className="mt-4" aria-hidden>
            <div className="relative h-2 rounded-full bg-line">
              <div className="absolute inset-y-0 left-0 rounded-full bg-warn/50" style={{ width: pos(t.inconsistent_max) }} />
              <div className="absolute inset-y-0 right-0 rounded-full bg-ok/50" style={{ left: pos(t.consistent_min) }} />
              <div className="absolute -top-1 h-4 w-1 rounded bg-ink" style={{ left: pos(c.similarity) }} />
            </div>
          </div>
        )}
        <p className="mt-3 text-sm text-ink-2">
          Similarity {c.similarity.toFixed(3)}.
          {t && ` Below ${t.inconsistent_max.toFixed(2)} counts as not matching, from ${t.consistent_min.toFixed(2)} as matching.`}
        </p>
      </div>
      <p className="mt-3 max-w-prose text-sm text-ink-2">{c.note} Model: {c.model}.</p>
    </div>
  );
}
