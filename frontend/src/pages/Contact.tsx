import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { TextArea } from "@/components/ui/Field";
import { EmptyState, ErrorNotice, Spinner } from "@/components/ui/Feedback";
import { useToast } from "@/context/ToastContext";
import { useAsync } from "@/hooks/useAsync";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, ApiError } from "@/services/api";
import { caseNumber, formatDate } from "@/utils/format";

const CATEGORIES = [
  { value: "incorrect_result", label: "A result looks wrong" },
  { value: "bug", label: "Something is broken" },
  { value: "feature_request", label: "I need a feature or module" },
  { value: "other", label: "Something else" },
];
const STATUS_TEXT = { new: "Waiting for review", reviewed: "Reviewed", dismissed: "Closed without action" } as const;

export default function Contact() {
  useDocumentTitle("Contact and feedback");
  const toast = useToast();
  const [params] = useSearchParams();
  const analysisParam = Number(params.get("analysis")) || null;
  const about = params.get("about");
  const [category, setCategory] = useState(CATEGORIES.some((c) => c.value === params.get("category")) ? params.get("category")! : "other");
  const [message, setMessage] = useState(about ? `About: ${about}\n\n` : "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const mine = useAsync(() => api.feedback.mine(), []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (message.trim().length < 5) return setError("Write at least a few words so the team can act on it.");
    setError(null);
    setBusy(true);
    try {
      await api.feedback.create({ category, message: message.trim(), analysis_id: analysisParam });
      toast.success("Feedback sent.");
      setMessage("");
      mine.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The feedback could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
      <div>
        <h1>Contact and feedback</h1>
        <p className="mt-3 text-ink-2">Tell the project team what is wrong or missing. Administrators read every message. Feedback is never used to retrain a model automatically.</p>

        <form onSubmit={submit} className="panel panel-pad mt-8 space-y-5" noValidate>
          <div>
            <label htmlFor="category" className="label">What is this about?</label>
            <select id="category" className="field" value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
          {analysisParam && <p className="rounded-control border border-line bg-raised px-3 py-2.5 text-sm text-ink-2">This message will be linked to {caseNumber(analysisParam)}.</p>}
          <TextArea label="Message" value={message} onChange={(e) => setMessage(e.target.value)} rows={7} maxLength={2000} error={error} hint="Up to 2,000 characters." />
          <div className="flex justify-end"><Button type="submit" busy={busy}><Send className="h-4 w-4" aria-hidden />Send feedback</Button></div>
        </form>
      </div>

      <section aria-labelledby="mine" className="lg:pt-[5.5rem]">
        <h2 id="mine" className="text-xl">Your messages</h2>
        <div className="panel mt-4">
          {mine.loading && !mine.data ? <div className="px-5"><Spinner label="Loading" /></div>
            : mine.error ? <div className="p-4"><ErrorNotice error={mine.error} onRetry={mine.reload} /></div>
            : mine.data && mine.data.length === 0 ? <EmptyState title="Nothing sent yet">Your messages and their review status will appear here.</EmptyState>
            : <ul>{mine.data?.map((f) => (
                <li key={f.id} className="border-t border-line p-4 first:border-t-0">
                  <p className="line-clamp-3 text-sm">{f.message}</p>
                  <p className="mt-2 text-xs text-ink-3">{CATEGORIES.find((c) => c.value === f.category)?.label}, {formatDate(f.created_at)}, <span className="text-ink-2">{STATUS_TEXT[f.status]}</span></p>
                </li>))}</ul>}
        </div>
      </section>
    </div>
  );
}
