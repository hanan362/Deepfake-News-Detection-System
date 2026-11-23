import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Globe } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { TextInput } from "@/components/ui/Field";
import { StatusPill } from "@/components/ui/StatusPill";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useModels } from "@/hooks/useModels";
import { takeDraft } from "@/utils/draft";
import { api, ApiError } from "@/services/api";

/** The address fields that can be checked without the server: a web address, not a file path or a search phrase. */
function localProblem(value: string): string | null {
  const v = value.trim();
  if (!v) return null;
  if (/\s/.test(v)) return "A web address has no spaces in it.";
  if (!/^https?:\/\//i.test(v)) return "Start the address with http:// or https://";
  return null;
}

export default function UrlAnalysis() {
  useDocumentTitle("Analyse a news address");
  const toast = useToast();
  const navigate = useNavigate();
  const { byModule } = useModels();
  const [url, setUrl] = useState(() => takeDraft("url"));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const entry = byModule("url");
  const off = entry?.status === "unavailable";
  const problem = localProblem(url);
  const canSubmit = !busy && url.trim().length > 0 && !problem && !off;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setBusy(true);
    try {
      const result = await api.analysis.url(url.trim());
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
          <h1>Analyse a news address</h1>
          {entry && <StatusPill status={entry.status} />}
        </div>
        <p className="mt-3 text-ink-2">Paste the web address of a news article. The server reads that one page, runs the text model on the article and describes the website it came from. The two results are shown side by side, never combined into one score.</p>

        <form onSubmit={submit} className="mt-8 space-y-5" noValidate>
          {off && <p className="rounded-control border border-bad/40 bg-bad/5 px-3 py-2.5 text-sm text-bad" role="alert">{entry?.description}</p>}
          {error && <p className="rounded-control border border-bad/40 bg-bad/5 px-3 py-2.5 text-sm text-bad" role="alert" data-testid="url-error">{error}</p>}
          <TextInput label="Article address" type="url" inputMode="url" autoComplete="off" spellCheck={false} placeholder="https://example.com/news/article" value={url} onChange={(e) => setUrl(e.target.value)} maxLength={1000} error={problem} hint="Public pages only. Addresses on private or internal networks are refused." />
          <div className="flex justify-end">
            <Button type="submit" busy={busy} disabled={!canSubmit}><Globe className="h-4 w-4" aria-hidden />Read and analyse</Button>
          </div>
          {busy && <p className="text-sm text-ink-2" aria-live="polite">Fetching the page. This can take up to 15 seconds.</p>}
        </form>
      </div>

      <aside className="space-y-6 lg:pt-[5.5rem]" aria-label="What to expect">
        <section className="panel panel-pad">
          <h2 className="text-xl">What happens</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>The page is downloaded once, with size and time limits. Nothing is crawled.</li>
            <li>The article text and the details the page declares (author, date) are extracted.</li>
            <li>The text model reads the extracted text.</li>
            <li>The website is compared with a small directory of recognised news organisations.</li>
          </ol>
        </section>
        <section className="panel panel-pad">
          <h2 className="text-xl">What it cannot do</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>Read pages that need JavaScript, a login or a subscription. Paste the text instead.</li>
            <li>Rate a website that is not in its directory. It says "not enough information", never "fake".</li>
            <li>Check whether the claims are true.</li>
          </ul>
        </section>
      </aside>
    </div>
  );
}
