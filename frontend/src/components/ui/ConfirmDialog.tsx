import { useEffect, useRef, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Button } from "./Button";

interface Props {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  tone?: "danger" | "primary";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, children, confirmLabel, tone = "danger", busy, onConfirm, onCancel }: Props) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && !busy && onCancel();
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, [open, busy, onCancel]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.12 }} onMouseDown={(e) => e.target === e.currentTarget && !busy && onCancel()}>
          <motion.div role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" className="panel w-full max-w-md p-6 shadow-2xl" initial={{ y: 12, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 8, opacity: 0 }} transition={{ duration: 0.16 }}>
            <h2 id="confirm-title" className="text-xl">{title}</h2>
            <div className="mt-2 text-sm text-ink-2">{children}</div>
            <div className="mt-6 flex justify-end gap-3">
              <Button ref={cancelRef} variant="quiet" onClick={onCancel} disabled={busy}>Cancel</Button>
              <Button variant={tone === "danger" ? "danger" : "primary"} onClick={onConfirm} busy={busy}>{confirmLabel}</Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
