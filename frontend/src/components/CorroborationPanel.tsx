import clsx from "clsx";
import { ExternalLink, Newspaper } from "lucide-react";
import type { Corroboration } from "@/types/api";
import { formatPercent } from "@/utils/format";

const STATUS: Record<Corroboration["status"], { label: string; tone: string }> = {
  corroborated: { label: "Reported by listed outlets", tone: "border-ok/40 text-ok" },
  disputed: { label: "A listed outlet reports something different", tone: "border-warn/50 text-warn" },
  not_found: { label: "No matching report found", tone: "border-line text-ink-2" },
  skipped: { label: "Not checked", tone: "border-line text-ink-3" },
  unavailable: { label: "Could not be checked", tone: "border-line text-ink-3" },
};

/** The headline-against-news check, shown as its own result: what was searched, what matched, the rule used and what it cannot show. */
export function CorroborationPanel({ c }: { c: Corroboration }) {
  const s = STATUS[c.status];
  return (
    <div className="max-w-3xl rounded-panel border border-line p-5" data-testid="corroboration" data-status={c.status}>
      <div className="flex flex-wrap items-center gap-3">
        <Newspaper className="h-5 w-5 text-ink-3" aria-hidden />
        <span className={clsx("pill", s.tone)} data-testid="corroboration-status">{s.label}</span>
      </div>
      {c.message && <p className="mt-3 text-ink-2">{c.message}</p>}
      {c.query && <p className="mt-2 text-sm text-ink-3">Searched for: “{c.query}”</p>}

      {c.outlets.length > 0 && (
        <ul className="mt-4 space-y-3" aria-label="Matching reports">
          {c.outlets.map((o) => (
            <li key={o.name} className="rounded-control border border-line p-4 text-sm" data-testid="corroboration-outlet">
              <p className="font-medium">{o.name}</p>
              <p className="mt-1 text-ink-2">Its headline: “{o.title}”</p>
              <p className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-3">
                <span>Words in common {formatPercent(o.overlap)}</span>
                <span>{o.relation === "same_story" ? `Says the same ${formatPercent(o.entailment)}` : `Says the opposite ${formatPercent(o.contradiction)}`}</span>
                {o.published && <span>{o.published}</span>}
                {o.url && <a href={o.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1">Open report <ExternalLink className="h-3 w-3" aria-hidden /></a>}
              </p>
            </li>
          ))}
        </ul>
      )}

      {c.status === "not_found" && (c.related?.length ?? 0) > 0 && (
        <div className="mt-4" data-testid="corroboration-related">
          <p className="text-sm font-medium">Related coverage, a different claim</p>
          <p className="mt-1 text-sm text-ink-2">These listed outlets reported on the same subject, but their headlines do not say what yours says. Read them and compare; they do not make your headline true or false.</p>
          <ul className="mt-3 space-y-2" aria-label="Related coverage">
            {c.related!.map((o) => (
              <li key={o.name} className="rounded-control border border-line p-3 text-sm">
                <p className="font-medium">{o.name}</p>
                <p className="mt-1 text-ink-2">“{o.title}”</p>
                <p className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-3">
                  <span>Words in common {formatPercent(o.overlap)}</span>
                  {o.published && <span>{o.published}</span>}
                  {o.url && <a href={o.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1">Open report <ExternalLink className="h-3 w-3" aria-hidden /></a>}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {c.status !== "skipped" && (
        <p className="mt-4 text-xs text-ink-3">
          {c.results_read} headlines read, {c.listed_outlet_results} from listed outlets
          {c.excluded_outlet ? `; ${c.excluded_outlet}, the site this article came from, was not counted` : ""}.
        </p>
      )}
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-ink-2">How this is decided and what it cannot show</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-2">
          <li>Compares {c.rules.compares}.</li>
          <li>Reported: {c.rules.corroborated}.</li>
          <li>Different: {c.rules.disputed}.</li>
          {c.rules.related && <li>Related: {c.rules.related}.</li>}
        </ul>
        <p className="mt-2 text-ink-2">{c.limits}</p>
      </details>
    </div>
  );
}
