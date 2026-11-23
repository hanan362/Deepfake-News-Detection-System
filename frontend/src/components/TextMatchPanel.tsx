import clsx from "clsx";
import { FileSearch } from "lucide-react";
import type { TextMatch } from "@/types/api";
import { formatPercent } from "@/utils/format";

const STATUS: Record<TextMatch["status"], { label: string; tone: string }> = {
  consistent: { label: "The text says what the headline says", tone: "border-ok/40 text-ok" },
  contradicts: { label: "The text says something different", tone: "border-warn/50 text-warn" },
  unrelated: { label: "The text is about something else", tone: "border-warn/50 text-warn" },
  details_differ: { label: "Names or numbers do not match", tone: "border-warn/50 text-warn" },
  not_stated: { label: "The headline is not clearly stated", tone: "border-line text-ink-2" },
  skipped: { label: "Not checked", tone: "border-line text-ink-3" },
  unavailable: { label: "Could not be checked", tone: "border-line text-ink-3" },
};

/** The text of the article read against its own headline: the sentences that matched best, the numbers and names that were missing, and the limits. */
export function TextMatchPanel({ m }: { m: TextMatch }) {
  const s = STATUS[m.status];
  return (
    <div className="max-w-3xl rounded-panel border border-line p-5" data-testid="text-match" data-status={m.status}>
      <div className="flex flex-wrap items-center gap-3">
        <FileSearch className="h-5 w-5 text-ink-3" aria-hidden />
        <span className={clsx("pill", s.tone)} data-testid="text-match-status">{s.label}</span>
      </div>
      {m.message && <p className="mt-3 text-ink-2">{m.message}</p>}
      {m.effect_note && <p className="mt-2 text-sm text-ink-2" data-testid="text-match-effect">{m.effect_note}</p>}
      {m.missing.length > 0 && (
        <p className="mt-2 text-sm text-ink-2" data-testid="text-match-missing">In the headline but not in the text: <strong>{m.missing.join(", ")}</strong></p>
      )}
      {m.best && (
        <div className="mt-4 rounded-control border border-line p-4 text-sm" data-testid="text-match-best">
          <p className="font-medium">{m.status === "consistent" ? "The sentences that say it" : "The sentences closest to the headline"}</p>
          <p className="mt-1 text-ink-2">“{m.best.text}”</p>
          <p className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-3">
            <span>Words in common {formatPercent(m.best.overlap)}</span>
            {/* when the text is about something else, the model's figures about it mean nothing, so they are not shown */}
            {m.status !== "unrelated" && <span>Says the same {formatPercent(m.best.entailment)}</span>}
            {m.status !== "unrelated" && <span>Says the opposite {formatPercent(m.best.contradiction)}</span>}
          </p>
        </div>
      )}
      {m.status !== "skipped" && m.sentences_read > 0 && <p className="mt-4 text-xs text-ink-3">The first {m.sentences_read} sentences of the text were read.</p>}
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-ink-2">How this is decided and what it cannot show</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-2">
          <li>Reads {m.rules.reads}.</li>
          <li>Matches: {m.rules.consistent}.</li>
          <li>Different: {m.rules.contradicts}.</li>
          <li>Other subject: {m.rules.unrelated}.</li>
          <li>Different details: {m.rules.details_differ}.</li>
        </ul>
        <p className="mt-2 text-ink-2">{m.limits}</p>
      </details>
    </div>
  );
}
