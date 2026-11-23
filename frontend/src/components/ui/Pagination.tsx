import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";

export function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);
  return (
    <nav className="flex items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm text-ink-2" aria-label="Pagination">
      <span>{total === 0 ? "No results" : `${from}-${to} of ${total}`}</span>
      <div className="flex items-center gap-2">
        <Button variant="quiet" size="sm" onClick={() => onPage(page - 1)} disabled={page <= 1} aria-label="Previous page">
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span aria-live="polite">Page {page} of {pages}</span>
        <Button variant="quiet" size="sm" onClick={() => onPage(page + 1)} disabled={page >= pages} aria-label="Next page">
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </nav>
  );
}
