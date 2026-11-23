import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Printer } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ErrorNotice, Skeleton } from "@/components/ui/Feedback";
import { rulingLine } from "@/components/VerdictRuling";
import { useAsync } from "@/hooks/useAsync";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api } from "@/services/api";
import { ANALYSIS_TYPE_LABEL, caseNumber, formatDate, formatPercent } from "@/utils/format";
import { useAnalysisActions } from "./AnalysisResult";

/** A formal, printable view of one analysis. "Download PDF" produces the same content from the server. */
export default function AnalysisReport() {
  const { id } = useParams();
  const analysisId = Number(id);
  const { data: a, error, loading, reload } = useAsync(() => api.analysis.get(analysisId), [analysisId]);
  useDocumentTitle(a ? `Report ${caseNumber(a.id)}` : "Report");
  const actions = useAnalysisActions(a);

  if (loading) return <div className="mx-auto max-w-3xl space-y-4"><Skeleton className="h-10 w-64" /><Skeleton className="h-96" /></div>;
  if (error || !a) return <div className="mx-auto max-w-3xl"><ErrorNotice error={error ?? new Error("Not found")} onRetry={reload} title="The report could not be loaded" /></div>;

  const d = a.details;
  const rows: [string, string][] = [
    ["Case", caseNumber(a.id)],
    ["Type", ANALYSIS_TYPE_LABEL[a.analysis_type] ?? a.analysis_type],
    ["Created", formatDate(a.created_at)],
    ["Result", a.verdict],
    ["Model confidence", a.confidence === null ? "Not applicable" : formatPercent(a.confidence)],
    ["Model", a.model ? `${a.model.name} ${a.model.version} (${a.model.status.replace("_", " ")})` : "-"],
  ];

  return (
    <div className="mx-auto max-w-3xl">
      <div className="no-print mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link to={`/analysis/${a.id}`} className="inline-flex items-center gap-2 text-sm"><ArrowLeft className="h-4 w-4" aria-hidden />Back to result</Link>
        <div className="flex gap-2.5">
          <Button variant="quiet" onClick={() => window.print()}><Printer className="h-4 w-4" aria-hidden />Print</Button>
          <Button onClick={actions.download} busy={actions.downloading}><Download className="h-4 w-4" aria-hidden />Download PDF</Button>
        </div>
      </div>

      <article className="print-doc panel panel-pad !p-8 sm:!p-10">
        <p className="text-sm text-ink-3">Deepfake News Detection System</p>
        <h1 className="mt-1 text-[2rem]">Analysis report, {caseNumber(a.id)}</h1>

        <dl className="mt-6 divide-y divide-line border-y border-line text-sm">
          {rows.map(([k, v]) => <div key={k} className="flex justify-between gap-6 py-2.5"><dt className="text-ink-2">{k}</dt><dd className="text-right">{v}</dd></div>)}
        </dl>

        {a.analysis_type === "url" && d?.url && (
          <>
            <h2 className="mt-8 text-xl">Web address</h2>
            <p className="mt-2 break-all">{a.source_url}</p>
            {d.url.final !== a.source_url && <p className="mt-1 break-all text-sm text-ink-2">Read from: {d.url.final}</p>}
            <p className="mt-2 text-sm text-ink-2">{d.url.extraction.words} words of article text were extracted{d.url.truncated ? " from a page that was cut at the size limit" : ""}. Declared author: {d.url.extraction.author ?? "none found"}. Declared date: {d.url.extraction.published ?? "none found"}.</p>
            {d.source && (
              <>
                <h2 className="mt-8 text-xl">The website</h2>
                <p className="mt-2"><span className="font-medium">{d.source.label}.</span> <span className="text-ink-2">{d.source.summary}</span></p>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink-2">{d.source.signals.map((s) => <li key={s.id}>{s.label} ({s.effect}): {s.detail}</li>)}</ul>
                <p className="mt-2 text-sm text-ink-2">Not checked: {d.source.not_checked.join(" ")}</p>
                <p className="mt-1 text-sm text-ink-2">{d.source.caveat}</p>
              </>
            )}
          </>
        )}

        {(a.headline || a.source_filename) && <><h2 className="mt-8 text-xl">Subject</h2><p className="mt-2">{a.headline || a.source_filename}</p></>}

        <h2 className="mt-8 text-xl">Reading of the result</h2>
        <p className="mt-2 text-ink-2">{rulingLine(a)}</p>

        {d?.corroboration && (
          <>
            <h2 className="mt-8 text-xl">Headline compared with news reports</h2>
            <p className="mt-2 text-sm"><span className="font-medium">{d.corroboration.status.replace("_", " ")}.</span> <span className="text-ink-2">{d.corroboration.message}</span></p>
            {d.corroboration.outlets.length > 0 && (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-2">{d.corroboration.outlets.map((o) => <li key={o.name}>{o.name}: “{o.title}” (words in common {formatPercent(o.overlap)}, {o.relation === "same_story" ? `says the same ${formatPercent(o.entailment)}` : `says the opposite ${formatPercent(o.contradiction)}`})</li>)}</ul>
            )}
            <p className="mt-2 text-xs text-ink-3">{d.corroboration.limits}</p>
          </>
        )}

        {d?.probabilities && (
          <p className="mt-3 text-sm text-ink-2">Model scores: fake {d.probabilities.fake.toFixed(3)}, real {d.probabilities.real.toFixed(3)}. A call needs {formatPercent(d.decision_rule?.threshold)} on one side. These are model scores, not the probability that the news is true.</p>
        )}

        {d?.explanation && (
          <>
            <h2 className="mt-8 text-xl">Terms that moved the score</h2>
            <p className="mt-2 text-sm"><span className="font-medium">Toward fake:</span> {d.explanation.toward_fake.map((t) => `${t.term} (${t.weight > 0 ? "+" : ""}${t.weight.toFixed(2)})`).join(", ") || "none"}</p>
            <p className="mt-1.5 text-sm"><span className="font-medium">Toward real:</span> {d.explanation.toward_real.map((t) => `${t.term} (${t.weight.toFixed(2)})`).join(", ") || "none"}</p>
          </>
        )}

        {a.analysis_type === "multimodal" && d?.fusion && (
          <>
            <h2 className="mt-8 text-xl">How the verdict was reached</h2>
            <p className="mt-2 text-sm text-ink-2">{d.fusion.rule}</p>
            <ul className="mt-2 list-disc pl-5 text-sm text-ink-2">{d.fusion.notes.map((n) => <li key={n}>{n}</li>)}</ul>
            {d.consistency && <p className="mt-3 text-sm text-ink-2">Image and text: {d.consistency.label ?? d.consistency.status}{d.consistency.similarity !== null ? `, similarity ${d.consistency.similarity.toFixed(3)}` : ""}. {d.consistency.note}</p>}
          </>
        )}

        {a.analysis_type === "evidence" && d?.claims && (
          <>
            <h2 className="mt-8 text-xl">Claims checked</h2>
            <ul className="mt-2 space-y-3 text-sm">
              {d.claims.map((c) => (
                <li key={c.claim}>
                  <p><span className="font-medium">{c.verdict}.</span> {c.claim}</p>
                  <p className="mt-1 text-ink-2">{c.reason}</p>
                  <ul className="mt-1 list-disc pl-5 text-ink-2">{c.evidence.map((e) => <li key={e.url + e.title}>{e.title} ({e.stance.replace("_", " ")}){e.rating ? `, rated ${e.rating} by ${e.publisher ?? "a fact-checker"}` : ""}</li>)}</ul>
                </li>
              ))}
            </ul>
          </>
        )}

        {d?.ela && (
          <>
            <h2 className="mt-8 text-xl">Measurements</h2>
            <p className="mt-2 text-sm text-ink-2">Mean error level {d.ela.mean.toFixed(2)}, highest {d.ela.max.toFixed(1)}, unevenness {d.ela.block_cv.toFixed(2)}.</p>
            <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-ink-2">{d.observations?.map((o) => <li key={o}>{o}</li>)}</ul>
          </>
        )}

        <h2 className="mt-8 text-xl">Limits</h2>
        <p className="mt-2 text-sm text-ink-2">{a.limitations}</p>
        <p className="mt-6 border-t border-line pt-4 text-xs text-ink-3">An automated aid from a student research prototype. It is not a fact-check and is not proof that content is real or fake.</p>
      </article>
    </div>
  );
}
