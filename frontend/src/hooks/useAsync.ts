import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/services/api";

export interface AsyncState<T> {
  data: T | null;
  error: ApiError | Error | null;
  loading: boolean;
  reload: () => void;
}

/** Run an async loader when `deps` change. Out-of-date responses are ignored so fast filter changes cannot show stale data. */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const latest = useRef(0);

  useEffect(() => {
    const run = ++latest.current;
    setLoading(true);
    setError(null);
    loader()
      .then((d) => {
        if (run === latest.current) setData(d);
      })
      .catch((e) => {
        if (run === latest.current) setError(e as Error);
      })
      .finally(() => {
        if (run === latest.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}
