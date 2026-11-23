import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";

type Kind = "success" | "error" | "info";
interface Toast {
  id: number;
  kind: Kind;
  message: string;
}
interface ToastApi {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const ICON = { success: CheckCircle2, error: TriangleAlert, info: Info } as const;
const COLOR = { success: "text-ok", error: "text-bad", info: "text-cyan" } as const;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const push = useCallback(
    (kind: Kind, message: string) => {
      const id = nextId.current++;
      setToasts((t) => [...t.slice(-3), { id, kind, message }]);
      window.setTimeout(() => dismiss(id), kind === "error" ? 8000 : 4500);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({ success: (m) => push("success", m), error: (m) => push("error", m), info: (m) => push("info", m) }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2" role="region" aria-label="Notifications" aria-live="polite">
        <AnimatePresence>
          {toasts.map((t) => {
            const Icon = ICON[t.kind];
            return (
              <motion.div
                key={t.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: 24 }}
                transition={{ duration: 0.18 }}
                className="pointer-events-auto flex items-start gap-3 rounded-panel border border-line bg-raised p-3.5 shadow-xl shadow-black/20"
                role={t.kind === "error" ? "alert" : "status"}
              >
                <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${COLOR[t.kind]}`} aria-hidden />
                <p className="flex-1 text-sm">{t.message}</p>
                <button className="rounded p-0.5 text-ink-3 hover:text-ink" onClick={() => dismiss(t.id)} aria-label="Dismiss notification">
                  <X className="h-4 w-4" />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
