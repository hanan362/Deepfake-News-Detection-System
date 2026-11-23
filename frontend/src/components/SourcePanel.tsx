import clsx from "clsx";
import { Check, CircleAlert, Minus } from "lucide-react";
import type { SourceAssessment, SourceSignal, UrlDetails } from "@/types/api";

const OUTCOME_TONE: Record<SourceAssessment["assessment"], string> = {
  recognised_publisher: "border-ok/40 bg-ok/5",
  declared_satire: "border-cyan/40 bg-cyan/5",
  lookalike: "border-warn/50 bg-warn/5",
  unknown: "border-line bg-panel",
};

const EFFECT_ICON = { supporting: Check, neutral: Minus, caution: CircleAlert } as const;
const EFFECT_TEXT: Record<SourceSignal["effect"], string> = { supporting: "text-ok", neutral: "text-ink-3", caution: "text-warn" };
const EFFECT_WORD: Record<SourceSignal["effect"], string> = { supporting: "Supporting", neutral: "Neutral", caution: "Caution" };

/**
 * What is known about the website an article came from. It is shown beside the text result and never merged into it:
 * there is no score, and an unfamiliar website is described as "not enough information", never as fake.
 */
export function SourcePanel({ source }: { source: SourceAssessment }) {
  return (
    <div>
      <div className={clsx("rounded-panel border p-5", OUTCOME_TONE[source.assessment])} data-testid="source-outcome" data-assessment={source.assessment}>
        <p className="font-display text-2xl font-medium leading-tight">{source.label}</p>
        <p className="mt-1 text-sm text-ink-3">{source.host}</p>
        <p className="mt-3 max-w-prose text-ink-2">{source.summary}</p>
        {source.resembles?.reason && <p className="mt-2 max-w-prose text-sm text-ink-2">{source.resembles.reason}</p>}
      </div>

      <h3 className="mt-6 text-lg">What was observed on the page</h3>
      <p className="mt-1 text-sm text-ink-2">Plain observations. Most are declared by the page itself, so anyone can add them, and none of them changes the outcome above.</p>
      <ul className="mt-3 divide-y divide-line rounded-panel border border-line text-sm">
        {source.signals.map((s) => {
          const Icon = EFFECT_ICON[s.effect];
          return (
            <li key={s.id} className="flex gap-3 px-4 py-3">
              <Icon className={clsx("mt-0.5 h-4 w-4 shrink-0", EFFECT_TEXT[s.effect])} aria-hidden />
              <div>
                <p><span className="font-medium">{s.label}</span> <span className="text-ink-3">({EFFECT_WORD[s.effect]})</span></p>
                <p className="mt-0.5 text-ink-2">{s.detail}</p>
              </div>
            </li>
          );
        })}
      </ul>

      <h3 className="mt-6 text-lg">What was not checked</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-2 marker:text-ink-3">
        {source.not_checked.map((n) => <li key={n}>{n}</li>)}
      </ul>
      <p className="mt-4 max-w-prose text-sm text-ink-2">{source.caveat}</p>
      <p className="mt-2 max-w-prose text-xs text-ink-3">Directory version {source.directory.version}, {source.directory.entries} entries. {source.directory.meaning}</p>
    </div>
  );
}

const METHOD_TEXT: Record<UrlDetails["url"]["extraction"]["method"], string> = {
  article_element: "the paragraphs inside the page's article element",
  paragraphs: "the longer paragraphs found on the page",
  plain_text: "the plain text of the page",
  none: "nothing, because no article paragraphs were found",
};

/** How the article text was obtained, so the reader can judge whether the text result applies to the whole article. */
export function ExtractionNote({ url }: { url: UrlDetails["url"] }) {
  const e = url.extraction;
  return (
    <div className="rounded-panel border border-line p-4 text-sm text-ink-2" data-testid="extraction-note">
      <p>
        <span className="font-medium text-ink">{e.words.toLocaleString()} words</span> were read from <span className="break-all">{url.final}</span> using {METHOD_TEXT[e.method]}.
        {url.truncated && " The page was larger than the size limit, so only its first part was read."}
        {url.redirects.length > 0 && ` The address redirected ${url.redirects.length} ${url.redirects.length === 1 ? "time" : "times"}.`}
      </p>
      <p className="mt-1.5">Declared author: {e.author ?? "none found"}. Declared date: {e.published ?? "none found"}. The text was extracted automatically and may include or leave out parts of the article. Compare it with the page if the result matters.</p>
    </div>
  );
}
