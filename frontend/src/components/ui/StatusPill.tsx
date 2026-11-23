import clsx from "clsx";
import { CircleDashed, CircleDot, FlaskConical, Hammer, ScanLine, TriangleAlert } from "lucide-react";
import { STATUS_LABEL } from "@/utils/format";
import type { ModuleStatus } from "@/types/api";

const STYLE: Record<string, { cls: string; Icon: typeof CircleDot }> = {
  trained_baseline: { cls: "border-ok/40 bg-ok/10 text-ok", Icon: CircleDot },
  pretrained: { cls: "border-ok/40 bg-ok/10 text-ok", Icon: CircleDot },
  heuristic: { cls: "border-cyan/40 bg-cyan/10 text-cyan", Icon: ScanLine },
  experimental: { cls: "border-violet/40 bg-violet/10 text-violet", Icon: FlaskConical },
  unavailable: { cls: "border-bad/40 bg-bad/10 text-bad", Icon: TriangleAlert },
  planned: { cls: "border-line bg-raised text-ink-2", Icon: Hammer },
};

/** A module's status. The icon and the words carry the meaning, so colour is never the only signal. */
export function StatusPill({ status, title }: { status: ModuleStatus | string; title?: string }) {
  const s = STYLE[status] ?? { cls: "border-line bg-raised text-ink-2", Icon: CircleDashed };
  return (
    <span className={clsx("pill", s.cls)} title={title}>
      <s.Icon className="h-3 w-3" aria-hidden />
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}
