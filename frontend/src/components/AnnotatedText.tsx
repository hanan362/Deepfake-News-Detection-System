import { useMemo } from "react";
import type { TermWeight } from "@/types/api";
import { highlightSegments } from "@/utils/highlight";

/** The submitted text with the words the model's explanation named marked in place. Two underline styles, not just two colours. */
export function AnnotatedText({ text, toward_fake, toward_real }: { text: string; toward_fake: TermWeight[]; toward_real: TermWeight[] }) {
  const segments = useMemo(() => highlightSegments(text, toward_fake, toward_real), [text, toward_fake, toward_real]);
  return (
    <div>
      <div className="exhibit max-h-80 overflow-auto p-5 font-sans text-[1.02rem] leading-[1.8]" tabIndex={0} dir="auto" aria-label="Submitted text with marked terms">
        {segments.map((s, i) =>
          s.tone ? (
            <mark
              key={i}
              data-tone={s.tone}
              title={s.tone === "fake" ? "Pushed the score toward fake" : "Pushed the score toward real"}
              className={
                s.tone === "fake"
                  ? "rounded-sm bg-bad/15 text-ink underline decoration-bad decoration-wavy decoration-1 underline-offset-4"
                  : "rounded-sm bg-ok/15 text-ink underline decoration-ok decoration-1 underline-offset-4"
              }
            >
              {s.text}
            </mark>
          ) : (
            <span key={i}>{s.text}</span>
          ),
        )}
      </div>
      <p className="mt-2.5 flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-2">
        <span><mark className="rounded-sm bg-bad/15 text-ink underline decoration-bad decoration-wavy decoration-1 underline-offset-4">wavy</mark> pushed toward fake</span>
        <span><mark className="rounded-sm bg-ok/15 text-ink underline decoration-ok decoration-1 underline-offset-4">solid</mark> pushed toward real</span>
        <span>Only the strongest terms are marked.</span>
      </p>
    </div>
  );
}
