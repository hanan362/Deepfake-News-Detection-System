import { useEffect, useState } from "react";

/** True once `active` has stayed true for `ms` milliseconds. Used to explain a long wait instead of showing a bare spinner. */
export function useSlowFlag(active: boolean, ms = 10_000): boolean {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!active) {
      setSlow(false);
      return;
    }
    const timer = setTimeout(() => setSlow(true), ms);
    return () => clearTimeout(timer);
  }, [active, ms]);
  return slow;
}
