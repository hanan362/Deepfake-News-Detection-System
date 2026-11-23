import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Download, FileText, MessageSquareWarning, Trash2 } from "lucide-react";
import { AnnotatedText } from "@/components/AnnotatedText";
import { ElaViewer } from "@/components/ElaViewer";
import { ReadingMeter } from "@/components/ReadingMeter";
import { CorroborationPanel } from "@/components/CorroborationPanel";
import { TextMatchPanel } from "@/components/TextMatchPanel";
import { EvidenceClaimCard } from "@/components/EvidencePanel";
import { ConsistencyPanel, FusionPanel } from "@/components/MultimodalPanels";
import { VideoSection } from "@/components/VideoPanels";
import { ExtractionNote, SourcePanel } from "@/components/SourcePanel";
import { TermList } from "@/components/TermList";
import { VerdictRuling } from "@/components/VerdictRuling";
import { Button, buttonClass } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ErrorNotice, Skeleton } from "@/components/ui/Feedback";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useAsync } from "@/hooks/useAsync";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, ApiError } from "@/services/api";
import type { Analysis } from "@/types/api";
import { ANALYSIS_TYPE_LABEL, caseNumber, formatDate } from "@/utils/format";
import { plainLimits } from "@/utils/plainLimits";

export function useAnalysisActions(a: Analysis | null) {
  const toast = useToast();
  const navigate = useNavigate();
  const [downloading, setDownloading] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function download() {
    if (!a) return;
    setDownloading(true);
    try {
      await api.analysis.reportPdf(a.id);
      toast.success("Report downloaded.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "The report could not be created.");
    } finally {
      setDownloading(false);
    }
  }

  async function remove() {
    if (!a) return;
    setDeleting(true);
    try {
      await api.analysis.remove(a.id);
      toast.success("Analysis deleted.");
      navigate("/history");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "The analysis could not be deleted.");
      setDeleting(false);
      setConfirm(false);
    }
  }
  return { downloading, download, confirm, setConfirm, deleting, remove };
}

export default function AnalysisResult() {
  const { id } = useParams();
  const analysisId = Number(id);
  const { data: a, error, loading, reload } = useAsync(() => api.analysis.get(analysisId), [analysisId]);
  useDocumentTitle(a ? caseNumber(a.id) : "Analysis result");
  const actions = useAnalysisActions(a);
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  if (loading) return <div className="mx-auto max-w-5xl space-y-4"><Skeleton className="h-10 w-72" /><Skeleton className="h-48" /><Skeleton className="h-64" /></div>;
  if (error || !a) {
    const missing = error instanceof ApiError && error.status === 404;
    return (
      <div className="mx-auto max-w-3xl">
        <ErrorNotice error={error ?? new Error("Not found")} onRetry={missing ? undefined : reload} title={missing ? "This analysis does not exist" : "The analysis could not be loaded"} />
        <Link to="/history" className="mt-6 inline-flex items-center gap-2 text-sm"><ArrowLeft className="h-4 w-4" aria-hidden />Back to history</Link>
      </div>
    );
  }

  const d = a.details;
  const isUrl = a.analysis_type === "url";
  const isEvidence = a.analysis_type === "evidence";
  const isMulti = a.analysis_type === "multimodal";
  const isText = a.analysis_type === "text" || isUrl; // a web address result carries the same writing-style result as pasted text
  const td = isMulti ? d?.text_result ?? null : d; // the writing-style result: the whole details for text and URL, a part of them for a pair
  const hasText = isText || (isMulti && !!td);
  const imd = isMulti ? d?.image_result ?? null : !isText && !isEvidence ? d : null; // the image indicators
  const subject = a.headline || a.source_filename || a.source_url || (isEvidence ? a.submitted_text?.slice(0, 120) : null) || "Untitled";

  return (
    <article className="mx-auto max-w-5xl" aria-labelledby="case-title">
      <Link to="/history" className="inline-flex items-center gap-2 text-sm"><ArrowLeft className="h-4 w-4" aria-hidden />Past checks</Link>

      <header className="mt-5">
        <p className="text-sm text-ink-2">{ANALYSIS_TYPE_LABEL[a.analysis_type] ?? a.analysis_type} on {formatDate(a.created_at)}, {caseNumber(a.id)}</p>
        <h1 id="case-title" className="mt-1.5 max-w-4xl text-[clamp(1.5rem,3.2vw,2.3rem)] [overflow-wrap:anywhere]" title={subject}>{subject.length > 160 ? `${subject.slice(0, 160)}...` : subject}</h1>
        {isUrl && a.source_url && <p className="mt-1 truncate text-sm text-ink-3" title={a.source_url} data-testid="source-url">{a.source_url}</p>}
        <div className="mt-5 flex flex-wrap gap-2.5">
          <Button variant="quiet" size="sm" onClick={actions.download} busy={actions.downloading}><Download className="h-4 w-4" aria-hidden />Download PDF</Button>
          <Link to={`/analysis/${a.id}/report`} className={buttonClass("quiet", "sm")}><FileText className="h-4 w-4" aria-hidden />Report view</Link>
          <Link to={`/contact?category=incorrect_result&analysis=${a.id}`} className={buttonClass("quiet", "sm")}><MessageSquareWarning className="h-4 w-4" aria-hidden />Report a problem</Link>
          <Button variant="danger" size="sm" onClick={() => actions.setConfirm(true)}><Trash2 className="h-4 w-4" aria-hidden />Delete</Button>
        </div>
      </header>

      <section className="mt-7" aria-labelledby="result-h">
        <h2 id="result-h" className="sr-only">Result</h2>
        <VerdictRuling analysis={a} />
        {isText && a.model?.status === "experimental" && (
          <p className="mt-3 max-w-2xl rounded-control border border-line bg-panel px-3 py-2.5 text-sm text-ink-2" data-testid="experimental-note">
            This result comes from an <strong>experimental</strong> model. It was not validated beyond one small collection, so it is a weak hint only.
          </p>
        )}
        {hasText && td?.probabilities && td.decision_rule && <div className="mt-5 max-w-2xl"><ReadingMeter probFake={td.probabilities.fake} threshold={td.decision_rule.threshold} plain /></div>}
        {isText && (
          <p className="mt-4 max-w-2xl text-sm text-ink-2" data-testid="check-facts-note">
            The writing-style reading does not check facts, so a true story can come out as Unverified; the headline comparison below looks for the same story at well-known outlets. To test whether the statements are true,{" "}
            <Link to="/analyze/evidence" state={a.submitted_text ? { text: a.submitted_text.slice(0, 5000) } : undefined}>check them against evidence</Link>.
          </p>
        )}
      </section>

      {isText && d?.corroboration && (
        <section className="mt-12" aria-labelledby="corr-h">
          <h2 id="corr-h" className="text-2xl">Do well-known outlets report it?</h2>
          <p className="mt-2 max-w-prose text-ink-2">This compares the headline with recent headlines from well-known news organisations. It shows that a story was reported, not that it is true.</p>
          {isAdmin && <p className="mt-2 max-w-prose text-sm text-ink-3" data-testid="admin-note">Administrators: a matching report can move the verdict one step. It lifts Unverified to Likely Real or softens Likely Fake to Unverified, and a report that says the opposite turns Likely Real into Unverified. It never makes a verdict Likely Fake.</p>}
          <div className="mt-5"><CorroborationPanel c={d.corroboration} /></div>
        </section>
      )}

      {isText && d?.text_match && d.text_match.status !== "skipped" && (
        <section className="mt-12" aria-labelledby="match-h">
          <h2 id="match-h" className="text-2xl">Does the text match its headline?</h2>
          <p className="mt-2 max-w-prose text-ink-2">A real headline can sit over a text that says something else. This reads the first sentences of the text against the headline and compares the numbers and names.</p>
          {isAdmin && <p className="mt-2 max-w-prose text-sm text-ink-3" data-testid="admin-note">Administrators: by default only a text that is unrelated to its headline stops a Likely Real. A contradiction or a different number or name is shown as a warning and leaves the verdict alone (set TEXT_MATCH_STRICT=true to let them change it). It never makes a verdict Likely Fake, and it cannot see false details that come after a text has agreed with its headline.</p>}
          <div className="mt-5"><TextMatchPanel m={d.text_match} /></div>
        </section>
      )}

      {a.analysis_type === "video" && <VideoSection a={a} />}

      {isMulti && d?.fusion && d.modalities && d.consistency && (
        <section className="mt-12" aria-labelledby="pair-h">
          <h2 id="pair-h" className="text-2xl">How the verdict was reached</h2>
          <div className="mt-4"><FusionPanel modalities={d.modalities} fusion={d.fusion} /></div>
          <h2 className="mt-10 text-2xl">Do the image and the text match?</h2>
          <div className="mt-4"><ConsistencyPanel c={d.consistency} /></div>
        </section>
      )}

      {isEvidence && d?.claims && (
        <section className="mt-12" aria-labelledby="claims-h">
          <h2 id="claims-h" className="text-2xl">{d.claims.length === 1 ? "The claim" : `The ${d.claims.length} claims checked`}</h2>
          <p className="mt-2 max-w-prose text-ink-2">
            {d.claims_picked_automatically ? "These claims were picked from your text by simple rules (statements with a name, a number or a reporting verb). If one is wrong, paste the exact claim instead. " : ""}
            Each verdict rests only on the sources listed under it.
          </p>
          <div className="mt-5 space-y-5">{d.claims.map((c, i) => <EvidenceClaimCard key={c.claim} claim={c} index={i} />)}</div>
          <p className="mt-4 text-sm text-ink-2">Stance model: {d.stance_model ?? "not available, so no stance was judged"}.</p>
        </section>
      )}

      {isUrl && d?.source && (
        <section className="mt-12" aria-labelledby="site-h">
          <h2 id="site-h" className="text-2xl">The website</h2>
          <p className="mt-2 max-w-prose text-ink-2">This describes where the article was published. A page on a well-known news organisation's own website can lift an Unverified reading to Likely Real, and never to Likely Fake.</p>
          <div className="mt-5"><SourcePanel source={d.source} /></div>
        </section>
      )}

      {isUrl && d?.url && (
        <section className="mt-12" aria-labelledby="read-h">
          <h2 id="read-h" className="text-2xl">How the article was read</h2>
          <div className="mt-4"><ExtractionNote url={d.url} /></div>
        </section>
      )}

      {isMulti && td && !td.probabilities && td.message && (
        <section className="mt-12" aria-labelledby="txt-h">
          <h2 id="txt-h" className="text-2xl">The text</h2>
          <p className="mt-2 max-w-prose text-ink-2">{td.message}</p>
        </section>
      )}

      {hasText && td?.explanation && a.submitted_text && (
        <section className="mt-12" aria-labelledby="why-h">
          <h2 id="why-h" className="text-2xl">What moved the score</h2>
          <p className="mt-2 max-w-prose text-ink-2">{isAdmin ? td.explanation.caution : "The words the check leaned on are marked below. They show what the writing resembles. They are not evidence that anything in the text is true or false."}</p>
          <div className="mt-5"><AnnotatedText text={a.submitted_text} toward_fake={td.explanation.toward_fake} toward_real={td.explanation.toward_real} /></div>
        </section>
      )}

      {imd?.ela && (
        <>
          <section className="mt-12" aria-labelledby="exhibit-h">
            <h2 id="exhibit-h" className="text-2xl">The image</h2>
            <p className="mt-2 max-w-prose text-ink-2">{imd.map_note} Bright areas changed more when the image was saved again at quality {imd.ela.quality}.</p>
            <div className="mt-5"><ElaViewer analysisId={a.id} /></div>
          </section>

          {imd.observations && imd.observations.length > 0 && (
            <section className="mt-12" aria-labelledby="obs-h">
              <h2 id="obs-h" className="text-2xl">What was noticed</h2>
              <ul className="mt-4 max-w-3xl space-y-3 text-sm">
                {imd.observations.map((o) => <li key={o} className="rounded-panel border border-line p-3.5 text-ink-2">{o}</li>)}
              </ul>
            </section>
          )}
        </>
      )}

      <section className="mt-12 rounded-panel border border-warn/50 bg-warn/5 p-5" aria-labelledby="limits-h">
        <h2 id="limits-h" className="text-xl">Limits of this result</h2>
        <div className="mt-2 max-w-prose space-y-2 text-sm text-ink-2">{plainLimits(a).map((t) => <p key={t}>{t}</p>)}</div>
      </section>

      {isAdmin && (
        <details className="mt-8 rounded-panel border border-line bg-panel" data-testid="technical-details">
          <summary className="flex cursor-pointer flex-wrap items-center gap-3 px-5 py-4 font-display text-lg font-semibold">
            Technical details <span className="pill border-line bg-raised text-ink-2">Administrators only</span>
          </summary>
          <div className="space-y-10 border-t border-line p-5">
            {hasText && td?.probabilities && td.decision_rule && <ReadingMeter probFake={td.probabilities.fake} threshold={td.decision_rule.threshold} />}
            {hasText && td?.explanation && <TermList toward_fake={td.explanation.toward_fake} toward_real={td.explanation.toward_real} />}
            {imd?.ela && (
              <div>
                <h3 id="measure-h">Measurements</h3>
                <dl className="mt-3 divide-y divide-line rounded-panel border border-line text-sm md:max-w-xl">
                  {[
                    ["Size", imd.image ? `${imd.image.width} x ${imd.image.height} px, ${imd.image.format}` : "-"],
                    ["Mean error level", imd.ela.mean.toFixed(2)],
                    ["Highest error level", imd.ela.max.toFixed(1)],
                    ["Unevenness across the image", imd.ela.block_cv.toFixed(2)],
                    ["Camera metadata", imd.metadata?.has_exif ? "Present" : "None found"],
                    ...(imd.metadata?.make ? [["Camera", `${imd.metadata.make} ${imd.metadata.model ?? ""}`.trim()]] : []),
                    ...(imd.metadata?.software ? [["Software", imd.metadata.software]] : []),
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-4 px-4 py-2.5"><dt className="text-ink-2">{k}</dt><dd className="text-right">{v}</dd></div>
                  ))}
                </dl>
              </div>
            )}
            <div>
              <h3>The model's own statement of its limits</h3>
              <p className="mt-2 max-w-prose text-sm text-ink-2">{a.limitations}</p>
            </div>
            {a.model && (
              <p className="flex flex-wrap items-center gap-2 text-sm text-ink-3">
                Produced by {a.model.name} {a.model.version} <StatusPill status={a.model.status} /> <Link to="/admin/models" className="ml-1">How it was measured</Link>
              </p>
            )}
          </div>
        </details>
      )}

      <ConfirmDialog open={actions.confirm} title="Delete this analysis?" confirmLabel="Delete analysis" busy={actions.deleting} onConfirm={actions.remove} onCancel={() => actions.setConfirm(false)}>
        {caseNumber(a.id)} and any file you uploaded for it will be removed permanently. This cannot be undone.
      </ConfirmDialog>
    </article>
  );
}
