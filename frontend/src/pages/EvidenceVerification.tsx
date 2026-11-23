import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Scale } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { TextArea } from "@/components/ui/Field";
import { StatusPill } from "@/components/ui/StatusPill";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useModels } from "@/hooks/useModels";
import { useSlowFlag } from "@/hooks/useSlowFlag";
import { SlowNotice } from "@/components/SlowNotice";
import { api, ApiError } from "@/services/api";
import { countWords } from "@/utils/text";

export default function EvidenceVerification() {
  useDocumentTitle("Check a claim against evidence");
  const toast = useToast();
  const navigate = useNavigate();
  const { byModule } = useModels();
  const location = useLocation();
  // A text or web address result can hand its text over, so the same words can be checked against evidence.
  const [text, setText] = useState(() => {
    const handed = (location.state as { text?: unknown } | null)?.text;
    return typeof handed === "string" ? handed.slice(0, 5000) : "";
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const slow = useSlowFlag(busy, 12_000);
  const entry = byModule("evidence");
  const off = entry?.status === "unavailable";
  const tooShort = text.trim().length < 10;
  const words = countWords(text);
  const canSubmit = !busy && !tooShort && text.length <= 5000 && !off;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setBusy(true);
    try {
      const result = await api.analysis.evidence(text.trim());
      toast.success("Analysis saved.");
      navigate(`/analysis/${result.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1>Check a claim against evidence</h1>
          {entry && <StatusPill status={entry.status} />}
        </div>
        <p className="mt-3 text-ink-2">Type one specific claim, or paste a passage and up to five claims are picked from it. The server looks for evidence, judges whether each passage supports or contradicts the claim, and shows every source. When nothing clear turns up, the answer is Insufficient Evidence.</p>

        <form onSubmit={submit} className="mt-8 space-y-5" noValidate>
          {off && <p className="rounded-control border border-bad/40 bg-bad/5 px-3 py-2.5 text-sm text-bad" role="alert">{entry?.description}</p>}
          {entry?.status === "heuristic" && <p className="rounded-control border border-warn/40 bg-warn/5 px-3 py-2.5 text-sm text-ink-2" data-testid="stance-off">{entry.description}</p>}
          {error && <p className="rounded-control border border-bad/40 bg-bad/5 px-3 py-2.5 text-sm text-bad" role="alert" data-testid="evidence-error">{error}</p>}
          <TextArea label="Claim or passage" value={text} onChange={(e) => setText(e.target.value)} rows={7} maxLength={5000} placeholder="For example: Jackie (2016 film) was directed by Peter Jackson." hint="English only. Specific statements with a name, a place or a number work best." />
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm text-ink-2" aria-live="polite">{words} {words === 1 ? "word" : "words"}</p>
            <Button type="submit" busy={busy} disabled={!canSubmit}><Scale className="h-4 w-4" aria-hidden />Check against evidence</Button>
          </div>
          {busy && <p className="text-sm text-ink-2" aria-live="polite">Searching for evidence. This can take several seconds.</p>}
          <SlowNotice show={slow} what="the evidence check" />
        </form>
      </div>

      <aside className="space-y-6 lg:pt-[5.5rem]" aria-label="What to expect">
        <section className="panel panel-pad">
          <h2 className="text-xl">What happens</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>Claims are picked from a long passage by simple rules you can read in the result.</li>
            <li>Wikipedia is searched, and published fact-checks too when the server has an API key.</li>
            <li>An inference model reads the closest sentence of each page against the claim.</li>
            <li>A stance counts only at 85% certainty and only for pages about the claim.</li>
          </ol>
        </section>
        <section className="panel panel-pad">
          <h2 className="text-xl">What it cannot do</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>Find news that Wikipedia does not cover. That gives Insufficient Evidence, not a verdict.</li>
            <li>Tell whether the evidence is itself correct.</li>
            <li>Always be right. A page about a similar subject can be read as contradicting a true claim, so open the sources before relying on a result.</li>
            <li>Check claims in other languages than English.</li>
          </ul>
        </section>
      </aside>
    </div>
  );
}
