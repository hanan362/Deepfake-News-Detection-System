import { Link } from "react-router-dom";
import { ErrorNotice, Skeleton } from "@/components/ui/Feedback";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/services/api";
import { datasetLabel, formatPercent, majorityAccuracy } from "@/utils/format";

/**
 * The text model's measured results, read live from the API: what it scored on its own kind of data next to what it
 * scored on a different, independent dataset. The gap between the two is the finding, so both are always shown.
 */
export function Scoreboard({ compact = false }: { compact?: boolean }) {
  const ev = useAsync(() => api.evaluation(), []);
  if (ev.error) return <ErrorNotice error={ev.error} onRetry={ev.reload} title="The measured results could not be loaded" />;
  if (ev.loading || !ev.data) return <div className="grid gap-4 sm:grid-cols-2"><Skeleton className="h-40" /><Skeleton className="h-40" /></div>;

  const { evaluation, dataset } = ev.data;
  const lr = evaluation.comparison[evaluation.deployed_model];
  const inDist = lr.test;
  const outDist = lr.external_liar2;

  const rows = [
    { key: "in", title: "On articles like its training data", sub: `${datasetLabel(dataset.name)}, ${inDist.n.toLocaleString()} held-out articles`, m: inDist },
    { key: "out", title: "On a different dataset", sub: `${datasetLabel(dataset.external_test_set.name)}, ${outDist.n.toLocaleString()} short political statements`, m: outDist },
  ];

  return (
    <div data-testid="scoreboard">
      <div className="grid gap-px overflow-hidden rounded-panel border border-line bg-line sm:grid-cols-2">
        {rows.map((r) => (
          <div key={r.key} className="bg-panel p-6">
            <p className="text-sm text-ink-2">{r.title}</p>
            <p className="mt-3 text-[3.25rem] font-medium leading-none">{formatPercent(r.m.accuracy, 1)}</p>
            <p className="mt-1 text-sm text-ink-2">accuracy</p>
            <dl className="mt-4 flex gap-6 text-sm">
              <div><dt className="text-ink-3">ROC AUC</dt><dd className="">{r.m.roc_auc.toFixed(3)}</dd></div>
              <div><dt className="text-ink-3">F1, fake class</dt><dd className="">{r.m.f1_fake.toFixed(3)}</dd></div>
              <div><dt className="text-ink-3">Constant answer</dt><dd className="">{formatPercent(majorityAccuracy(r.m.confusion_matrix), 1)}</dd></div>
            </dl>
            <p className="mt-4 text-xs text-ink-3">{r.sub}</p>
          </div>
        ))}
      </div>
      {!compact && (
        <p className="mt-4 max-w-3xl text-sm text-ink-2">
          A random guess scores 50% accuracy and an AUC of 0.5. “Constant answer” is the accuracy of giving the more common label every time. The model reads its own kind of articles very well.{" "}
          {outDist.accuracy > majorityAccuracy(outDist.confusion_matrix)
            ? "On the other dataset it is only slightly better than a constant answer."
            : "On the other dataset it does not beat a constant answer, and its AUC is close to a coin flip."}{" "}
          This is why the system asks for long English articles, withholds a call when unsure, and shows these numbers to the administrators.{" "}
          <Link to="/admin/models">See the full evaluation</Link>.
        </p>
      )}
    </div>
  );
}
