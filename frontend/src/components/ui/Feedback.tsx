import type { ReactNode } from "react";
import { Loader2, RefreshCw, TriangleAlert } from "lucide-react";
import { Button } from "./Button";

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2.5 py-10 text-ink-2" role="status">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-raised ${className}`} aria-hidden />;
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="px-4 py-12 text-center">
      <p className="font-display text-xl">{title}</p>
      {children && <div className="mx-auto mt-2 max-w-md text-sm text-ink-2">{children}</div>}
      {action && <div className="mt-5 flex justify-center gap-3">{action}</div>}
    </div>
  );
}

export function ErrorNotice({ error, onRetry, title = "This could not be loaded" }: { error: Error; onRetry?: () => void; title?: string }) {
  return (
    <div className="flex items-start gap-3 rounded-panel border border-bad/40 bg-bad/5 p-4" role="alert">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-bad" aria-hidden />
      <div className="flex-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-0.5 text-sm text-ink-2">{error.message}</p>
        {onRetry && (
          <Button variant="quiet" size="sm" className="mt-3" onClick={onRetry}>
            <RefreshCw className="h-3.5 w-3.5" aria-hidden /> Try again
          </Button>
        )}
      </div>
    </div>
  );
}
