import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, X } from "lucide-react";
import { ActivityChart } from "@/components/ActivityChart";
import { HorizontalBars } from "@/components/HorizontalBars";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorNotice, Skeleton } from "@/components/ui/Feedback";
import { Pagination } from "@/components/ui/Pagination";
import { StatusPill } from "@/components/ui/StatusPill";
import { useToast } from "@/context/ToastContext";
import { useAsync } from "@/hooks/useAsync";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, ApiError } from "@/services/api";
import { caseNumber, formatDate, MODULE_LABEL } from "@/utils/format";

const CATEGORY: Record<string, string> = { incorrect_result: "Result looks wrong", bug: "Something is broken", feature_request: "Feature or module request", other: "Other" };
const STATUS_FILTERS = [["new", "Waiting"], ["reviewed", "Reviewed"], ["dismissed", "Closed"], ["", "All"]] as const;

export default function Admin() {
  useDocumentTitle("Administration");
  const toast = useToast();
  const stats = useAsync(() => api.admin.stats(), []);
  const [fbStatus, setFbStatus] = useState<string>("new");
  const feedback = useAsync(() => api.admin.feedback(fbStatus || undefined), [fbStatus]);
  const [auditPage, setAuditPage] = useState(1);
  const audit = useAsync(() => api.admin.audit({ page: auditPage, page_size: 10 }), [auditPage]);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function review(id: number, status: "reviewed" | "dismissed") {
    setBusyId(id);
    try {
      await api.admin.reviewFeedback(id, status);
      toast.success(status === "reviewed" ? "Marked as reviewed." : "Closed without action.");
      feedback.reload();
      stats.reload();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "The feedback could not be updated.");
    } finally {
      setBusyId(null);
    }
  }

  const s = stats.data;
  return (
    <div className="mx-auto max-w-6xl">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div><h1>Administration</h1><p className="mt-2 text-ink-2">Counts across the whole system. Individual users' analyses and files are not shown here.</p></div>
        <Link to="/admin/users" className="btn btn-primary">Manage users</Link>
      </header>

      {stats.error ? <div className="mt-8"><ErrorNotice error={stats.error} onRetry={stats.reload} /></div> : !s ? <div className="mt-8 grid gap-4 sm:grid-cols-4"><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /></div> : (
        <>
          <section className="mt-8 grid gap-px overflow-hidden rounded-panel border border-line bg-line sm:grid-cols-2 lg:grid-cols-4" aria-label="Totals">
            {[
              ["Registered users", s.users.total, `${s.users.active} active, ${s.users.admins} admin`],
              ["New in 7 days", s.users.new_last_7_days, "accounts created"],
              ["Analyses", s.analyses.total, `${s.analyses.by_type.text ?? 0} text, ${s.analyses.by_type.image ?? 0} image`],
              ["Feedback waiting", s.feedback.new ?? 0, `${s.feedback.reviewed ?? 0} reviewed, ${s.feedback.dismissed ?? 0} closed`],
            ].map(([label, value, sub]) => (
              <div key={label as string} className="bg-panel p-5">
                <p className="text-sm text-ink-2">{label}</p>
                <p className="mt-2 text-[2.5rem] font-medium leading-none tabular-nums">{value}</p>
                <p className="mt-2 text-sm text-ink-3">{sub}</p>
              </div>
            ))}
          </section>

          <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
            <section className="panel panel-pad" aria-labelledby="act"><h2 id="act" className="mb-4 text-xl">Analyses per day</h2><ActivityChart data={s.analyses.daily} /></section>
            <section className="panel panel-pad" aria-labelledby="out"><h2 id="out" className="mb-4 text-xl">Outcomes</h2><HorizontalBars items={Object.entries(s.analyses.by_verdict).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value)} /></section>
          </div>

          <section className="panel mt-6 overflow-x-auto" aria-labelledby="mod">
            <h2 id="mod" className="px-5 pt-5 text-xl">Modules</h2>
            <table className="mt-3">
              <thead><tr><th className="th">Module</th><th className="th">Model</th><th className="th">Version</th><th className="th">Status</th></tr></thead>
              <tbody>{s.models.map((m) => <tr key={m.module} className="row"><td className="td">{MODULE_LABEL[m.module]}</td><td className="td text-ink-2">{m.name}</td><td className="td text-ink-2">{m.version}</td><td className="td"><StatusPill status={m.status} /></td></tr>)}</tbody>
            </table>
          </section>
        </>
      )}

      <section className="panel mt-6" aria-labelledby="fb">
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-5">
          <h2 id="fb" className="text-xl">Feedback</h2>
          <div className="flex gap-1.5" role="group" aria-label="Filter feedback">
            {STATUS_FILTERS.map(([v, label]) => (
              <button key={label} type="button" aria-pressed={fbStatus === v} onClick={() => setFbStatus(v)} className={`rounded-control px-3 py-1.5 text-sm ${fbStatus === v ? "bg-ink text-canvas font-semibold" : "text-ink-2 hover:bg-raised"}`}>{label}</button>
            ))}
          </div>
        </div>
        {feedback.error ? <div className="p-5"><ErrorNotice error={feedback.error} onRetry={feedback.reload} /></div> : !feedback.data ? <div className="p-5"><Skeleton className="h-24" /></div> : feedback.data.length === 0 ? <EmptyState title="No feedback here">Nothing matches this filter.</EmptyState> : (
          <ul className="mt-3">
            {feedback.data.map((f) => (
              <li key={f.id} className="border-t border-line px-5 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 max-w-2xl">
                    <p className="whitespace-pre-wrap text-sm">{f.message}</p>
                    <p className="mt-2 text-xs text-ink-3">{CATEGORY[f.category] ?? f.category}, from {f.username ?? "a deleted user"}, {formatDate(f.created_at)}{f.analysis_id ? `, about ${caseNumber(f.analysis_id)}` : ""}</p>
                  </div>
                  {f.status === "new" ? (
                    <div className="flex gap-2">
                      <Button size="sm" variant="quiet" onClick={() => review(f.id, "reviewed")} disabled={busyId === f.id}><Check className="h-4 w-4" aria-hidden />Mark reviewed</Button>
                      <Button size="sm" variant="ghost" onClick={() => review(f.id, "dismissed")} disabled={busyId === f.id}><X className="h-4 w-4" aria-hidden />Close</Button>
                    </div>
                  ) : <span className="text-sm text-ink-2">{f.status === "reviewed" ? "Reviewed" : "Closed without action"}</span>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel mt-6 overflow-hidden" aria-labelledby="aud">
        <h2 id="aud" className="px-5 pt-5 text-xl">Audit log</h2>
        <p className="px-5 pt-1 text-sm text-ink-2">Security and account events. Analysis content is never written to the log.</p>
        {audit.error ? <div className="p-5"><ErrorNotice error={audit.error} onRetry={audit.reload} /></div> : !audit.data ? <div className="p-5"><Skeleton className="h-32" /></div> : audit.data.items.length === 0 ? <EmptyState title="No events yet" /> : (
          <>
            <div className="mt-3 overflow-x-auto">
              <table>
                <thead><tr><th className="th">When</th><th className="th">Who</th><th className="th">Event</th><th className="th">Target</th><th className="th">Address</th></tr></thead>
                <tbody>{audit.data.items.map((a) => <tr key={a.id} className="row"><td className="td whitespace-nowrap text-ink-2">{formatDate(a.created_at)}</td><td className="td">{a.user ?? "-"}</td><td className="td">{a.action}</td><td className="td text-ink-2">{a.entity ? `${a.entity} ${a.entity_id ?? ""}` : "-"}</td><td className="td text-ink-2">{a.ip_address ?? "-"}</td></tr>)}</tbody>
              </table>
            </div>
            <Pagination page={auditPage} pageSize={10} total={audit.data.total} onPage={setAuditPage} />
          </>
        )}
      </section>
    </div>
  );
}
