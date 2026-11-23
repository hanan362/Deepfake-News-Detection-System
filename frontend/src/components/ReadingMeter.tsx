import { motion, useReducedMotion } from "framer-motion";
import { formatPercent } from "@/utils/format";

interface Props {
  probFake: number;
  threshold: number;
  /** For ordinary readers: the same bar with the words but no percentages. The numbers are for administrators. */
  plain?: boolean;
}

/**
 * Where the model's score sits between "real" and "fake", with the zones that decide the verdict drawn in.
 * The needle is the model's probability; it is not the probability that the story is true.
 */
export function ReadingMeter({ probFake, threshold, plain = false }: Props) {
  const reduce = useReducedMotion();
  const lo = (1 - threshold) * 100;
  const hi = threshold * 100;
  const pos = Math.min(100, Math.max(0, probFake * 100));
  const label = plain
    ? probFake >= threshold ? "The writing leans clearly towards fake." : probFake <= 1 - threshold ? "The writing leans clearly towards real." : "The writing does not lean clearly either way."
    : `Model leaning: ${formatPercent(probFake)} fake, ${formatPercent(1 - probFake)} real. A call needs at least ${formatPercent(threshold)} either way.`;

  return (
    <figure aria-label="Model reading">
      <div role="img" aria-label={label} className={`relative h-3 ${plain ? "mt-2" : "mt-8"}`}>
        <div className="absolute inset-0 flex gap-0.5 overflow-hidden rounded-full">
          <div style={{ width: `${lo}%` }} className="bg-ok/35" />
          <div style={{ width: `${hi - lo}%` }} className="bg-warn/30" />
          <div style={{ width: `${100 - hi}%` }} className="bg-bad/35" />
        </div>
        <motion.div
          className="absolute top-1/2 h-6 w-1 -translate-y-1/2 rounded-sm bg-ink ring-2 ring-panel"
          initial={reduce ? false : { left: "50%" }}
          animate={{ left: `${pos}%` }}
          transition={{ type: "spring", stiffness: 70, damping: 16, delay: 0.15 }}
          style={{ marginLeft: -2 }}
          data-testid="meter-needle"
        />
        {!plain && <span className="absolute -top-6 text-xs text-ink-2" style={{ left: `${lo}%`, transform: "translateX(-50%)" }}>{formatPercent(1 - threshold)}</span>}
        {!plain && <span className="absolute -top-6 text-xs text-ink-2" style={{ left: `${hi}%`, transform: "translateX(-50%)" }}>{formatPercent(threshold)}</span>}
      </div>
      <figcaption className="mt-2.5 flex justify-between text-xs text-ink-2">
        <span>Leans real</span>
        <span>Not sure</span>
        <span>Leans fake</span>
      </figcaption>
      {!plain && <p className="mt-3 text-sm text-ink-2">
        The model puts <span className="font-medium text-ink">{formatPercent(probFake)}</span> on fake and{" "}
        <span className="font-medium text-ink">{formatPercent(1 - probFake)}</span> on real. It only makes a call at {formatPercent(threshold)} or more.
      </p>}
    </figure>
  );
}
