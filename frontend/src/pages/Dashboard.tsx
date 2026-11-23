import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { VerdictBadge } from "@/components/VerdictRuling";
import { buttonClass } from "@/components/ui/Button";
import { EmptyState, ErrorNotice, Skeleton } from "@/components/ui/Feedback";
import { CHECKS } from "@/config/checks";
import { useAuth } from "@/context/AuthContext";
import { useAsync } from "@/hooks/useAsync";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useModels } from "@/hooks/useModels";
import { api } from "@/services/api";
import { caseNumber, formatDate, verdictBand, type Band } from "@/utils/format";

const TYPE_COUNTS: [string, string][] = [["text", "Articles"], ["url", "Links"], ["image", "Photos"], ["video", "Videos"], ["multimodal", "Photos with captions"], ["evidence", "Claim checks"]];
const BAND_BG: Record<Band, string> = { real: "bg-band-real", fake: "bg-band-fake", unsure: "bg-band-unsure", flag: "bg-band-flag" };

/** How the answers so far split, as one bar. The words and numbers sit under it, so the colours are not the only signal. */
function Mix({ byVerdict, total }: { byVerdict: Record<string, number>; total: number }) {
  const rows = Object.entries(byVerdict).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
  if (total === 0 || rows.length === 0) return null;
  return (
    <div>
      <div className="flex h-3 gap-0.5 overflow-hidden rounded-full" role="img" aria-label={rows.map(([v, n]) => `${v}: ${n}`).join(", ")}>
        {rows.map(([v, n]) => <div key={v} className={BAND_BG[verdictBand(v)]} style={{ width: `${(n / total) * 100}%` }} />)}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
        {rows.map(([v, n]) => (
          <li key={v} className="flex items-center gap-2"><span className={`h-2.5 w-2.5 rounded-sm ${BAND_BG[verdictBand(v)]}`} aria-hidden /><span className="text-ink-2">{v}</span><span className="font-semibold tabular-nums">{n}</span></li>
        ))}
      </ul>
    </div>
  );
}

export default function Dashboard() {
  useDocumentTitle("Home");
  const { user } = useAuth();
  const { byModule } = useModels();
  const stats = useAsync(() => api.dashboard(), []);
  const name = user?.full_name?.split(" ")[0] || user?.username;

  return (
    <div className="mx-auto max-w-5xl">
      <header>
        <h1>What would you like to check, {name}?</h1>
        <p className="mt-3 text-ink-2">Pick what you have. Every check is saved to your account and nobody else can open it.</p>
      </header>

      <ul className="mt-8 grid gap-x-10 gap-y-3 sm:grid-cols-2" aria-label="Kinds of check">
        {CHECKS.map(({ module, title, to, Icon }) => {
          const m = byModule(module);
          const off = m?.status === "unavailable";
          return (
            <li key={module}>
              <Link to={to} className="group flex h-full gap-4 rounded-panel border border-line bg-panel p-4 text-ink hover:border-ink hover:no-underline">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-control bg-primary text-on-primary"><Icon className="h-5 w-5" aria-hidden /></span>
                <span className="min-w-0">
                  <span className="flex flex-wrap items-center gap-2 font-display text-[1.05rem] font-bold">
                    {title}
                    {m?.status === "experimental" && <span className="pill border-line bg-raised font-sans text-ink-2">Experimental</span>}
                    {off && <span className="pill border-line bg-raised font-sans text-ink-2">Not available</span>}
                  </span>
                  <span className="mt-0.5 block text-sm text-ink-2">{off ? "Switched off on this server at the moment." : m?.description}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>

      {stats.error ? (
        <div className="mt-10"><ErrorNotice error={stats.error} onRetry={stats.reload} title="Your past checks could not be loaded" /></div>
      ) : stats.loading || !stats.data ? (
        <div className="mt-10 space-y-3"><Skeleton className="h-6 w-56" /><Skeleton className="h-40" /></div>
      ) : (
        <section className="mt-12" aria-labelledby="recent">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 id="recent">Your checks so far</h2>
            <p className="text-ink-2"><span className="font-display text-2xl font-bold text-ink" data-testid="total-analyses">{stats.data.total_analyses}</span> saved</p>
          </div>

          {stats.data.total_analyses === 0 ? (
            <div className="panel mt-5">
              <EmptyState title="No checks yet" action={<Link to="/analyze/text" className={buttonClass("primary")}>Check your first article <ArrowRight className="h-4 w-4" aria-hidden /></Link>}>
                Paste a news article or upload a photo. Each result is saved here with its reasons and its limits.
              </EmptyState>
            </div>
          ) : (
            <>
              <div className="mt-5"><Mix byVerdict={stats.data.by_verdict} total={stats.data.total_analyses} /></div>
              <ul className="mt-5 flex flex-wrap gap-2" aria-label="By kind of check">
                {TYPE_COUNTS.map(([type, label]) => (
                  <li key={type}>
                    <Link to={`/history?analysis_type=${type}`} className="pill border-line bg-panel !px-3 !py-1 text-ink-2 hover:border-ink hover:no-underline">
                      {label} <span className="font-bold text-ink" data-testid={`total-${type}`}>{stats.data?.by_type[type] ?? 0}</span>
                    </Link>
                  </li>
                ))}
              </ul>
              <div className="panel mt-6 overflow-hidden">
                {stats.data.recent.length === 0 ? (
                  <p className="px-5 py-8 text-sm text-ink-2">Your most recent checks will be listed here.</p>
                ) : (
                  <ul>
                    {stats.data.recent.map((a, i) => (
                      <li key={a.id} className={i ? "border-t border-line" : ""}>
                        <Link to={`/analysis/${a.id}`} className="flex items-center gap-4 px-5 py-3.5 text-ink hover:bg-raised hover:no-underline">
                          <span className="min-w-0 flex-1 truncate font-medium">{a.headline || a.source_filename || "Untitled"}</span>
                          <VerdictBadge verdict={a.verdict} />
                          <span className="hidden w-40 shrink-0 text-right text-sm text-ink-2 md:block">{formatDate(a.created_at)}</span>
                          <span className="sr-only">{caseNumber(a.id)}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="border-t border-line px-5 py-3 text-sm"><Link to="/history" className="font-semibold">See all past checks</Link></div>
              </div>
            </>
          )}
        </section>
      )}
    </div>
  );
}
