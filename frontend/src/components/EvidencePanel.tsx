import clsx from "clsx";
import { ExternalLink } from "lucide-react";
import type { EvidenceClaim, EvidenceItem } from "@/types/api";
import { formatPercent } from "@/utils/format";
import { VerdictBadge } from "./VerdictRuling";

const STANCE_LABEL: Record<EvidenceItem["stance"], string> = {
  supports: "Supports the claim", contradicts: "Contradicts the claim", unclear: "Not clear either way", not_relevant: "Not about this claim", other_subject: "Same name, different subject",
  not_assessed: "Stance not judged", published_rating: "Published rating",
};
const STANCE_STYLE: Record<EvidenceItem["stance"], string> = {
  supports: "border-ok/40 text-ok", contradicts: "border-bad/40 text-bad", unclear: "border-line text-ink-2", not_relevant: "border-line text-ink-3", other_subject: "border-line text-ink-3",
  not_assessed: "border-line text-ink-3", published_rating: "border-cyan/40 text-cyan",
};
const PROVIDER_NAME: Record<string, string> = { wikipedia: "Wikipedia", google_fact_check: "Published fact-checks (Google Fact Check Tools)" };
const STATUS_TEXT = { ok: "searched", no_results: "searched, nothing found", not_configured: "not searched", error: "could not be searched" } as const;

/** One claim, its verdict, the sources that were searched and every passage found, with its stance and how it was judged. */
export function EvidenceClaimCard({ claim, index }: { claim: EvidenceClaim; index: number }) {
  return (
    <article className="rounded-panel border border-line p-5" data-testid="evidence-claim" aria-labelledby={`claim-${index}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h3 id={`claim-${index}`} className="max-w-prose text-lg">{claim.claim}</h3>
        <VerdictBadge verdict={claim.verdict} />
      </div>
      <p className="mt-2 text-sm text-ink-2">{claim.reason}</p>

      <ul className="mt-4 space-y-1 text-sm" aria-label="Sources searched">
        {claim.providers.map((p) => (
          <li key={p.provider} className="flex flex-wrap gap-x-2 text-ink-2" data-testid="provider-status">
            <span className="font-medium text-ink">{PROVIDER_NAME[p.provider] ?? p.provider}:</span> {STATUS_TEXT[p.status]}.
            {(p.status === "not_configured" || p.status === "error") && <span>{p.message}</span>}
          </li>
        ))}
      </ul>

      {claim.evidence.length > 0 && (
        <ul className="mt-4 space-y-3">
          {claim.evidence.map((e) => (
            <li key={`${e.provider}-${e.url}-${e.title}`} className="rounded-control border border-line p-4 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">{e.title}</p>
                <span className={clsx("pill", STANCE_STYLE[e.stance])}>{STANCE_LABEL[e.stance]}</span>
              </div>
              {e.kind === "fact_check" && <p className="mt-1.5 text-ink-2">{e.publisher ?? "A fact-checker"} rated it: <span className="font-medium text-ink">{e.rating ?? "no rating given"}</span>. This is the publisher's own rating; the system does not interpret it.</p>}
              {e.best_sentence && <p className="mt-1.5 text-ink-2">Closest sentence: “{e.best_sentence}”</p>}
              {!e.best_sentence && e.excerpt && <p className="mt-1.5 line-clamp-3 text-ink-2">{e.excerpt}</p>}
              <p className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-3">
                <span>Word overlap with the claim {formatPercent(e.relevance)}</span>
                {e.stance_probabilities && <span>Entails {formatPercent(e.stance_probabilities.entailment)}, contradicts {formatPercent(e.stance_probabilities.contradiction)}</span>}
                {e.url && <a href={e.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1">Open source <ExternalLink className="h-3 w-3" aria-hidden /></a>}
              </p>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
