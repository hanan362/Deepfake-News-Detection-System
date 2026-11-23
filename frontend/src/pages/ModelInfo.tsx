import { Link } from "react-router-dom";
import { Scoreboard } from "@/components/Scoreboard";
import { ErrorNotice, Skeleton } from "@/components/ui/Feedback";
import { StatusPill } from "@/components/ui/StatusPill";
import { useAsync } from "@/hooks/useAsync";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useAdminModels } from "@/hooks/useModels";
import { api } from "@/services/api";
import { datasetLabel, formatDate, formatNumber, formatPercent, majorityAccuracy, MODULE_LABEL, STATUS_LABEL } from "@/utils/format";

const MODEL_NAME: Record<string, string> = {
  logistic_regression: "Logistic regression",
  naive_bayes: "Naive Bayes",
  linear_svm: "Linear SVM",
  random_forest: "Random forest",
};

export default function ModelInfo() {
  useDocumentTitle("Models and measurements");
  const models = useAdminModels();
  const ev = useAsync(() => api.evaluation(), []);
  const urduInstalled = models.byModule("text_ur")?.status === "experimental";
  const videoInstalled = models.byModule("video")?.status === "experimental";
  const vid = useAsync(() => (videoInstalled ? api.videoEvaluation() : Promise.resolve(null)), [videoInstalled]);
  const ur = useAsync(() => (urduInstalled ? api.urduEvaluation() : Promise.resolve(null)), [urduInstalled]);

  return (
    <div className="mx-auto max-w-6xl">
      <h1>Models and measurements</h1>
      <p className="mt-3 max-w-3xl text-ink-2">Every module, whether it exists in this build, and what was measured. Numbers on this page are read from the evaluation the training script saved. They are not typed in by hand.</p>

      <section className="mt-10" aria-labelledby="modules-h">
        <h2 id="modules-h" className="text-2xl">Modules</h2>
        {models.error ? <div className="mt-4"><ErrorNotice error={models.error} onRetry={models.reload} /></div> : !models.data ? <Skeleton className="mt-4 h-64" /> : (
          <div className="panel mt-4 overflow-x-auto">
            <table>
              <thead><tr><th className="th">Module</th><th className="th">Status</th><th className="th">Method</th><th className="th">What it does</th></tr></thead>
              <tbody>
                {models.data.models.map((m) => (
                  <tr key={m.module} className="row align-top">
                    <td className="td whitespace-nowrap font-medium">{MODULE_LABEL[m.module]}</td>
                    <td className="td whitespace-nowrap"><StatusPill status={m.status} /></td>
                    <td className="td text-ink-2">{m.algorithm ?? m.name}{m.language ? `, ${m.language}` : ""}</td>
                    <td className="td max-w-md text-ink-2">{m.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {models.data && (
          <dl className="mt-5 grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
            {Object.entries(models.data.status_meanings).map(([k, v]) => (
              <div key={k}><dt className="font-medium">{STATUS_LABEL[k] ?? k}</dt><dd className="text-ink-2">{v}</dd></div>
            ))}
          </dl>
        )}
      </section>

      <section className="mt-14" aria-labelledby="score-h">
        <h2 id="score-h" className="text-2xl">How the text model performs</h2>
        <p className="mt-2 max-w-3xl text-ink-2">The deployed model is {ev.data ? MODEL_NAME[ev.data.evaluation.deployed_model] ?? ev.data.evaluation.deployed_model : "..."}. It was tested twice: on held-out articles from its training dataset, and on a second dataset it had never seen.</p>
        <div className="mt-5"><Scoreboard compact /></div>
      </section>

      {ev.data && (
        <>
          <section className="mt-14" aria-labelledby="cmp-h">
            <h2 id="cmp-h" className="text-2xl">Four classifiers, same data</h2>
            <p className="mt-2 max-w-3xl text-ink-2">All four were trained on the same TF-IDF features and tested on the same two sets. Logistic regression was deployed because its score can be explained exactly, term by term, and its probabilities can be calibrated.</p>
            <div className="panel mt-4 overflow-x-auto">
              <table>
                <thead>
                  <tr><th className="th" rowSpan={2}>Classifier</th><th className="th text-center" colSpan={2}>Held-out articles</th><th className="th text-center" colSpan={2}>Different dataset</th><th className="th text-right" rowSpan={2}>Time per text</th></tr>
                  <tr><th className="th text-right">Accuracy</th><th className="th text-right">ROC AUC</th><th className="th text-right">Accuracy</th><th className="th text-right">ROC AUC</th></tr>
                </thead>
                <tbody>
                  {Object.entries(ev.data.evaluation.comparison).map(([k, v]) => (
                    <tr key={k} className="row">
                      <td className="td">{MODEL_NAME[k] ?? k}{k === ev.data!.evaluation.deployed_model && <span className="ml-2 text-xs text-cyan">deployed</span>}</td>
                      <td className="td text-right">{formatPercent(v.test.accuracy, 1)}</td>
                      <td className="td text-right">{v.test.roc_auc.toFixed(3)}</td>
                      <td className="td text-right">{formatPercent(v.external_liar2.accuracy, 1)}</td>
                      <td className="td text-right">{v.external_liar2.roc_auc.toFixed(3)}</td>
                      <td className="td text-right text-ink-2">{v.inference_ms_per_doc < 0.01 ? "under 0.01" : v.inference_ms_per_doc.toFixed(2)} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-14 grid gap-8 lg:grid-cols-2" aria-labelledby="data-h">
            <div>
              <h2 id="data-h" className="text-2xl">The data</h2>
              <dl className="mt-4 divide-y divide-line rounded-panel border border-line text-sm">
                {[
                  ["Training set", `${datasetLabel(ev.data.dataset.name)} (${ev.data.dataset.license})`],
                  ["Cleaned articles", `${formatNumber(ev.data.dataset.rows_clean.train)} train, ${formatNumber(ev.data.dataset.rows_clean.validation)} validation, ${formatNumber(ev.data.dataset.rows_clean.test)} test`],
                  ["Features", `${ev.data.evaluation.features.type}, ${ev.data.evaluation.features.ngram_range.join("-")} word n-grams, ${formatNumber(ev.data.evaluation.features.vocabulary_size)} terms`],
                  ["Different dataset", `${datasetLabel(ev.data.dataset.external_test_set.name)}, ${formatNumber(ev.data.dataset.external_test_set.rows)} statements, median ${ev.data.dataset.external_test_set.median_tokens} words`],
                  ["Trained", formatDate(ev.data.evaluation.trained_at)],
                ].map(([k, v]) => <div key={k} className="flex justify-between gap-6 px-4 py-2.5"><dt className="shrink-0 text-ink-2">{k}</dt><dd className="text-right">{v}</dd></div>)}
              </dl>
              <p className="mt-3 text-sm text-ink-2">{ev.data.dataset.notes}</p>
            </div>
            <div>
              <h2 className="text-2xl">How to read these numbers</h2>
              <p className="mt-4 text-ink-2">The first set of numbers measures how well the model separates fake from real among articles drawn from the same collection it learned from. The second set uses a different kind of text: short political statements judged by fact-checkers. Because the model transfers so poorly, a high score on the first set should not be read as a general ability to spot fake news.</p>
              {(() => {
                const lr = ev.data.evaluation.comparison[ev.data.evaluation.deployed_model];
                const constant = majorityAccuracy(lr.external_liar2.confusion_matrix);
                return (
                  <p className="mt-3 text-sm text-ink-2" data-testid="constant-answer-note">
                    “Constant answer” is the accuracy of giving the more common label every time, with no model at all. On the different dataset that is {formatPercent(constant, 1)}, and the model scores {formatPercent(lr.external_liar2.accuracy, 1)}.
                    {lr.external_liar2.accuracy > constant ? " The model is above it, but only slightly." : " The model does not beat it."}
                  </p>
                );
              })()}
              <p className="mt-3 text-sm text-ink-2">Calibration, measured as expected calibration error (lower is better): {ev.data.evaluation.calibration_logistic_regression.ece_test?.toFixed(3) ?? "n/a"} on the held-out articles and {ev.data.evaluation.calibration_logistic_regression.ece_external_liar2?.toFixed(3) ?? "n/a"} on the different dataset. The model's probabilities are only trustworthy on text like its training data, and they are never the chance that a story is true.</p>
              <p className="mt-3 text-sm"><Link to="/admin/methodology">How it was built and tested</Link></p>
            </div>
          </section>
        </>
      )}
      {ev.error && <div className="mt-10"><ErrorNotice error={ev.error} onRetry={ev.reload} title="The evaluation could not be loaded" /></div>}

      {ur.data && (
        <section className="mt-14" aria-labelledby="ur-h" data-testid="urdu-section">
          <h2 id="ur-h" className="text-2xl">The Urdu model (experimental)</h2>
          <p className="mt-2 max-w-3xl text-ink-2">A separate model reads Urdu text. It was trained on one small collection of {formatNumber(ur.data.dataset.rows_clean.train)} articles and tested on {formatNumber(ur.data.evaluation.test.n)} others from the same collection. There is no second Urdu collection to test it against, so nothing here shows that it works on Urdu news from other sources. That is why it is labelled experimental.</p>
          <div className="mt-5 grid gap-8 lg:grid-cols-2">
            <dl className="divide-y divide-line rounded-panel border border-line text-sm">
              {[
                ["Accuracy on held-out articles", `${formatPercent(ur.data.evaluation.test.accuracy, 1)} (95% range ${formatPercent(ur.data.evaluation.test.accuracy_ci95[0], 1)} to ${formatPercent(ur.data.evaluation.test.accuracy_ci95[1], 1)})`],
                ["ROC AUC", `${ur.data.evaluation.test.roc_auc.toFixed(3)} (95% range ${ur.data.evaluation.test.roc_auc_ci95[0].toFixed(3)} to ${ur.data.evaluation.test.roc_auc_ci95[1].toFixed(3)})`],
                ["Constant answer", formatPercent(ur.data.evaluation.baselines.majority_accuracy, 1)],
                ["Article length alone, ROC AUC", ur.data.evaluation.baselines.length_only.roc_auc.toFixed(3)],
                ["Decided at the confidence threshold", `${formatPercent(ur.data.evaluation.decision_coverage.share_decided, 0)} of articles, ${formatPercent(ur.data.evaluation.decision_coverage.accuracy_when_decided, 1)} correct when decided`],
                ["Calibration error (ECE)", ur.data.evaluation.calibration.ece_test.toFixed(3)],
                ["Features", `${ur.data.evaluation.features.analyzer} ${ur.data.evaluation.features.ngram_range.join("-")}-grams, ${formatNumber(ur.data.evaluation.features.vocabulary_size)} terms`],
                ["Trained", formatDate(ur.data.evaluation.trained_at)],
              ].map(([k, v]) => <div key={k} className="flex justify-between gap-6 px-4 py-2.5"><dt className="shrink-0 text-ink-2">{k}</dt><dd className="text-right">{v}</dd></div>)}
            </dl>
            <div className="text-sm text-ink-2">
              <p>{ur.data.dataset.notes}</p>
              <p className="mt-3">In the training split, {formatPercent(ur.data.dataset.pairing.nearest_neighbour_has_opposite_label, 0)} of articles have a near-identical partner with the opposite label. A plain cross-validation therefore scored below chance, and the model was selected with a pair-aware one instead.</p>
              <p className="mt-3">Accuracy by news category on the held-out articles: {Object.entries(ur.data.evaluation.by_category_accuracy).map(([c, v]) => `${c} ${formatPercent(v.accuracy, 0)} (${v.n})`).join(", ")}.</p>
            </div>
          </div>
        </section>
      )}

      {vid.data && (() => {
        const e = vid.data.evaluation;
        const rows = (["calibration", "test", "fresh"] as const).filter((k) => e.results[k]).map((k) => ({ key: k, r: e.results[k]!, label: e.sets[k] }));
        const NAME = { calibration: "Calibration videos (thresholds were set here)", test: "Held-out Celeb-DF videos (optimistic)", fresh: "Different dataset: Google DeepFakeDetection" } as const;
        return (
          <section className="mt-14" aria-labelledby="vid-h" data-testid="video-eval-section">
            <h2 id="vid-h" className="text-2xl">The video model (experimental)</h2>
            <p className="mt-2 max-w-3xl text-ink-2">Each sampled frame is scored on its own by {e.model}, a third-party image classifier fine-tuned on FaceForensics++ faces that this project did not train. The frame scores are then combined ({e.aggregator.replace(/_/g, " ")} of the scores). It is frame-based: nothing here learns motion or timing. The two decision thresholds and the way scores are combined were chosen on {e.calibration.chosen_on_videos} Celeb-DF videos and not changed afterwards.</p>
            <div className="panel mt-5 overflow-x-auto">
              <table>
                <thead><tr><th className="th">Videos</th><th className="th">Count</th><th className="th">ROC AUC over the video (95% range)</th><th className="th">One frame only, AUC</th><th className="th">Decided</th><th className="th">Correct when decided</th></tr></thead>
                <tbody>
                  {rows.map(({ key, r }) => (
                    <tr key={key} className="row align-top" data-testid={`video-eval-${key}`}>
                      <td className="td">{NAME[key]}</td>
                      <td className="td whitespace-nowrap">{r.n_real} real, {r.n_fake} fake</td>
                      <td className="td whitespace-nowrap">{r.video_auc?.toFixed(3)}{r.video_auc_ci95 ? ` (${r.video_auc_ci95[0].toFixed(2)} to ${r.video_auc_ci95[1].toFixed(2)})` : ""}</td>
                      <td className="td">{r.single_frame_auc?.toFixed(3)}</td>
                      <td className="td whitespace-nowrap">{r.decision_rule.decided} of {r.decision_rule.n}</td>
                      <td className="td">{r.decision_rule.accuracy_on_decided === null ? "-" : formatPercent(r.decision_rule.accuracy_on_decided, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul className="mt-5 max-w-3xl list-disc space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
              <li>Chance is 0.5 AUC and 50% accuracy: every set has as many real as fake videos. The intervals are wide because each set has only tens of videos.</li>
              <li>The decision thresholds ({e.calibration.real_max ?? "none"} and {e.calibration.fake_min ?? "none"}) aim for {formatPercent(e.calibration.target_precision, 0)} correct on each side. On the different dataset the rate falls short of that, so expect the scores to shift on other footage.</li>
              <li>The second row is optimistic: this model was picked from five candidates while looking at part of that sample, and the model's own validation set may overlap with Celeb-DF.</li>
              <li>A first pretrained candidate (dima806/deepfake_vs_real_image_detection) scored at chance on Celeb-DF (frame AUC 0.47) and was dropped.</li>
              <li>Not tested: news broadcast footage, heavy compression, other manipulation methods, lip-sync or voice fakes. Audio is not analysed.</li>
            </ul>
          </section>
        );
      })()}

      {models.data && (
        <section className="mt-14" aria-labelledby="lim-h">
          <h2 id="lim-h" className="text-2xl">Known limits</h2>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-ink-2 marker:text-ink-3">
            {models.data.models.filter((m) => m.limitations?.length).flatMap((m) => m.limitations!.map((l) => <li key={`${m.module}-${l}`}><span className="text-ink">{MODULE_LABEL[m.module]}:</span> {l}</li>))}
          </ul>
        </section>
      )}
    </div>
  );
}
