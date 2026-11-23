import { ShieldAlert, ShieldCheck } from "lucide-react";
import type { TermWeight } from "@/types/api";

function Column({ title, tone, terms, max }: { title: string; tone: "fake" | "real"; terms: TermWeight[]; max: number }) {
  const Icon = tone === "fake" ? ShieldAlert : ShieldCheck;
  const bar = tone === "fake" ? "bg-bad" : "bg-ok";
  return (
    <div>
      <h3 className="flex items-center gap-2 font-sans text-sm font-medium">
        <Icon className={`h-4 w-4 ${tone === "fake" ? "text-bad" : "text-ok"}`} aria-hidden />
        {title}
      </h3>
      {terms.length === 0 ? (
        <p className="mt-3 text-sm text-ink-2">No terms in this text moved the score in this direction.</p>
      ) : (
        <ul className="mt-3 space-y-2.5">
          {terms.map((t) => (
            <li key={t.term} className="grid grid-cols-[minmax(0,9rem)_1fr_3.2rem] items-center gap-3 text-sm">
              <span className="truncate" title={t.term}>{t.term}</span>
              <span className="h-1.5 overflow-hidden rounded-full bg-raised" aria-hidden>
                <span className={`block h-full rounded-full ${bar}`} style={{ width: `${Math.max(6, (Math.abs(t.weight) / max) * 100)}%` }} />
              </span>
              <span className="text-right text-ink-2">{t.weight > 0 ? "+" : ""}{t.weight.toFixed(2)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function TermList({ toward_fake, toward_real }: { toward_fake: TermWeight[]; toward_real: TermWeight[] }) {
  const max = Math.max(0.0001, ...toward_fake.map((t) => Math.abs(t.weight)), ...toward_real.map((t) => Math.abs(t.weight)));
  return (
    <div className="grid gap-8 md:grid-cols-2">
      <Column title="Pushed the score toward fake" tone="fake" terms={toward_fake} max={max} />
      <Column title="Pushed the score toward real" tone="real" terms={toward_real} max={max} />
    </div>
  );
}
