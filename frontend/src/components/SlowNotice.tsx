/** Shown when an analysis has been running for a while. The first use of a heavy check downloads and loads a model. */
export function SlowNotice({ show, what }: { show: boolean; what: string }) {
  if (!show) return null;
  return (
    <p className="max-w-2xl rounded-control border border-warn/40 bg-warn/5 px-3 py-2.5 text-sm text-ink-2" role="status" data-testid="slow-notice">
      Still working. The first time {what} is used, the server downloads and loads a model, which can take several minutes. Keep this page open: the result
      appears here when it is ready. Later checks are much faster.
    </p>
  );
}
