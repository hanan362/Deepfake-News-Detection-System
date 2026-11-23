import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Eraser, ScanText } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { TextArea, TextInput } from "@/components/ui/Field";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useModels } from "@/hooks/useModels";
import { takeDraft } from "@/utils/draft";
import { useSlowFlag } from "@/hooks/useSlowFlag";
import { SlowNotice } from "@/components/SlowNotice";
import { api, ApiError } from "@/services/api";
import { countWords, looksArabicScript, looksUrdu } from "@/utils/text";

export default function TextAnalysis() {
  useDocumentTitle("Analyse an article");
  const toast = useToast();
  const navigate = useNavigate();
  const { data: models, byModule } = useModels();
  const [headline, setHeadline] = useState("");
  const [text, setText] = useState(() => takeDraft("text"));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const slow = useSlowFlag(busy, 12_000);

  const limits = models?.limits;
  const minWords = limits?.min_text_words ?? 60;
  const maxChars = limits?.max_text_chars ?? 50_000;
  const words = useMemo(() => countWords(headline + " " + text), [headline, text]);
  const arabicScript = useMemo(() => looksArabicScript(text), [text]);
  const urduSupported = (limits?.text_languages ?? ["en"]).includes("ur");
  const urdu = useMemo(() => urduSupported && looksUrdu(text), [urduSupported, text]);
  // Arabic-script text is accepted only when it is Urdu and the Urdu model is installed.
  const arabic = arabicScript && !urdu;
  const modelDown = byModule("text")?.status === "unavailable";
  const tooShort = words < minWords;
  const tooLong = text.length > maxChars;
  const canSubmit = !busy && !tooShort && !tooLong && !arabic && !modelDown;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setBusy(true);
    try {
      const result = await api.analysis.text(text, headline.trim() || undefined);
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
        <h1>Analyse an article</h1>
        <p className="mt-3 text-ink-2">Paste the full text of a news article. The model reads its writing and reports how closely it resembles articles it was trained on as fake or real.</p>

        <form onSubmit={submit} className="mt-8 space-y-5" noValidate>
          {modelDown && <p className="rounded-control border border-bad/40 bg-bad/5 px-3 py-2.5 text-sm text-bad" role="alert">{byModule("text")?.description}</p>}
          {error && <p className="rounded-control border border-bad/40 bg-bad/5 px-3 py-2.5 text-sm text-bad" role="alert">{error}</p>}
          <TextInput label="Headline" value={headline} onChange={(e) => setHeadline(e.target.value)} maxLength={500} optional hint="Adding the headline lets the system also look for the same story at well-known news outlets. Only the headline is sent to a news search; the article text stays on this server." />
          <TextArea label="Article text" value={text} onChange={(e) => setText(e.target.value)} rows={14} placeholder="Paste the article here" dir="auto" error={arabic ? (urduSupported ? "This looks like Arabic or Persian, or Urdu with too few Urdu letters to be sure. The models read English and Urdu only." : "This looks like Urdu or another Arabic-script language. No model for it is installed, so the system reads English only.") : tooLong ? `The text is longer than ${maxChars.toLocaleString()} characters.` : null} />
          {urdu && <p className="rounded-control border border-line bg-panel px-3 py-2.5 text-sm text-ink-2" data-testid="urdu-note">Urdu detected. The Urdu model is <strong>experimental</strong>: it was trained on one small collection and could not be tested on any other, so treat its result as a weak hint.</p>}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className={`text-sm ${tooShort ? "text-ink-2" : "text-ok"}`} aria-live="polite" data-testid="word-count">
              {words} {words === 1 ? "word" : "words"}
              {tooShort ? `, at least ${minWords} needed` : ""}
            </p>
            <div className="flex gap-3">
              <Button variant="quiet" onClick={() => { setText(""); setHeadline(""); setError(null); }} disabled={!text && !headline}><Eraser className="h-4 w-4" aria-hidden />Clear</Button>
              <Button type="submit" busy={busy} disabled={!canSubmit}><ScanText className="h-4 w-4" aria-hidden />Analyse text</Button>
            </div>
          </div>
          <SlowNotice show={slow && headline.trim().length > 0} what="the headline check" />
        </form>
      </div>

      <aside className="space-y-6 lg:pt-[5.5rem]" aria-label="What to expect">
        <section className="panel panel-pad">
          <h2 className="text-xl">What you get</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>A call of Likely Fake or Likely Real only when the reading is clearly one-sided. Otherwise: Unverified.</li>
            <li>The words that moved the score, marked in your text.</li>
            <li>A PDF report you can keep.</li>
          </ul>
        </section>
        <section className="panel panel-pad">
          <h2 className="text-xl">What it cannot do</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>Check whether the claims are true.</li>
            <li>Read languages other than English{urduSupported ? " and (experimentally) Urdu" : ""}, or text under {minWords} words.</li>
            <li>Work well on text unlike the articles it learned from, such as short statements or posts.</li>
          </ul>
        </section>
      </aside>
    </div>
  );
}
