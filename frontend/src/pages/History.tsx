import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Download, Search, Trash2 } from "lucide-react";
import { VerdictBadge } from "@/components/VerdictRuling";
import { Button, buttonClass } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState, ErrorNotice, Spinner } from "@/components/ui/Feedback";
import { Pagination } from "@/components/ui/Pagination";
import { useToast } from "@/context/ToastContext";
import { useAsync } from "@/hooks/useAsync";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, ApiError } from "@/services/api";
import type { Analysis } from "@/types/api";
import { ANALYSIS_TYPE_LABEL, caseNumber, formatDate } from "@/utils/format";

const PAGE_SIZE = 10;
const VERDICTS = ["Likely Fake", "Likely Real", "Unverified", "Indicators Only", "Supported", "Contradicted", "Mixed Evidence", "Insufficient Evidence", "Mismatch Flagged"];

export default function History() {
  useDocumentTitle("Past checks");
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const type = params.get("analysis_type") ?? "";
  const verdict = params.get("verdict") ?? "";
  const q = params.get("q") ?? "";
  const page = Math.max(1, Number(params.get("page") ?? 1) || 1);

  // The search box types freely; the list (and the address bar) update after a short pause.
  const [draft, setDraft] = useState(q);
  useEffect(() => setDraft(q), [q]);
  useEffect(() => {
    if (draft === q) return;
    const t = window.setTimeout(() => update({ q: draft, page: "" }), 300);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]);

  function update(changes: Record<string, string>) {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(changes)) (v ? next.set(k, v) : next.delete(k));
    setParams(next, { replace: true });
  }

  const list = useAsync(() => api.analysis.list({ page, page_size: PAGE_SIZE, analysis_type: type || undefined, verdict: verdict || undefined, q: q || undefined }), [page, type, verdict, q]);

  const [toDelete, setToDelete] = useState<Analysis | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  async function confirmDelete() {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await api.analysis.remove(toDelete.id);
      toast.success(`${caseNumber(toDelete.id)} deleted.`);
      setToDelete(null);
      // Step back a page if the last row of the last page was removed.
      if (list.data && list.data.items.length === 1 && page > 1) update({ page: String(page - 1) });
      else list.reload();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "The analysis could not be deleted.");
    } finally {
      setDeleting(false);
    }
  }

  async function download(a: Analysis) {
    setDownloadingId(a.id);
    try {
      await api.analysis.reportPdf(a.id);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "The report could not be created.");
    } finally {
      setDownloadingId(null);
    }
  }

  const filtered = Boolean(type || verdict || q);

  return (
    <div className="mx-auto max-w-6xl">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div><h1>Past checks</h1><p className="mt-2 text-ink-2">Every check you have saved. Only you can see them.</p></div>
        <Link to="/analyze/text" className={buttonClass("primary")}>New analysis</Link>
      </header>

      <div className="mt-8 flex flex-wrap items-center gap-3" role="search">
        <div className="relative min-w-[16rem] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" aria-hidden />
          <input type="search" className="field pl-9" placeholder="Search headlines, text and file names" aria-label="Search history" value={draft} onChange={(e) => setDraft(e.target.value)} />
        </div>
        <select className="field w-auto" aria-label="Filter by type" value={type} onChange={(e) => update({ analysis_type: e.target.value, page: "" })}>
          <option value="">All types</option><option value="text">Text</option><option value="url">News URL</option><option value="evidence">Evidence</option><option value="multimodal">Multimodal</option><option value="video">Video</option><option value="image">Image</option>
        </select>
        <select className="field w-auto" aria-label="Filter by result" value={verdict} onChange={(e) => update({ verdict: e.target.value, page: "" })}>
          <option value="">All results</option>{VERDICTS.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        {filtered && <Button variant="ghost" onClick={() => { setDraft(""); setParams({}, { replace: true }); }}>Clear filters</Button>}
      </div>

      <section className="panel mt-5 overflow-hidden" aria-label="Analyses">
        {list.error ? (
          <div className="p-5"><ErrorNotice error={list.error} onRetry={list.reload} title="History could not be loaded" /></div>
        ) : list.loading && !list.data ? (
          <div className="px-5"><Spinner label="Loading history" /></div>
        ) : list.data && list.data.items.length === 0 ? (
          <EmptyState title={filtered ? "Nothing matches these filters" : "No analyses yet"} action={filtered ? undefined : <Link to="/analyze/text" className={buttonClass("primary")}>Analyse an article</Link>}>
            {filtered ? "Try a different search, or clear the filters." : "Results you save will be listed here."}
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead><tr><th className="th">Case</th><th className="th">Subject</th><th className="th">Type</th><th className="th">Result</th><th className="th">Date</th><th className="th"><span className="sr-only">Actions</span></th></tr></thead>
              <tbody>
                {list.data?.items.map((a) => (
                  <tr key={a.id} className="row">
                    <td className="td whitespace-nowrap"><Link to={`/analysis/${a.id}`}>{caseNumber(a.id)}</Link></td>
                    <td className="td max-w-[22rem] truncate" title={a.headline ?? a.source_filename ?? ""}>{a.headline || a.source_filename || "Untitled"}</td>
                    <td className="td text-ink-2">{ANALYSIS_TYPE_LABEL[a.analysis_type]?.replace(/ (analysis|inspection|check)$/, "") ?? a.analysis_type}</td>
                    <td className="td"><VerdictBadge verdict={a.verdict} /></td>
                    <td className="td whitespace-nowrap text-ink-2">{formatDate(a.created_at)}</td>
                    <td className="td">
                      <div className="flex justify-end gap-1.5">
                        <Button variant="ghost" size="sm" onClick={() => download(a)} busy={downloadingId === a.id} aria-label={`Download PDF report for ${caseNumber(a.id)}`}><Download className="h-4 w-4" aria-hidden /></Button>
                        <Button variant="ghost" size="sm" onClick={() => setToDelete(a)} aria-label={`Delete ${caseNumber(a.id)}`}><Trash2 className="h-4 w-4" aria-hidden /></Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {list.data && list.data.total > 0 && <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPage={(p) => update({ page: p > 1 ? String(p) : "" })} />}
      </section>

      <ConfirmDialog open={toDelete !== null} title="Delete this analysis?" confirmLabel="Delete analysis" busy={deleting} onConfirm={confirmDelete} onCancel={() => setToDelete(null)}>
        {toDelete && <>{caseNumber(toDelete.id)} and any file you uploaded for it will be removed permanently. This cannot be undone.</>}
      </ConfirmDialog>
    </div>
  );
}
