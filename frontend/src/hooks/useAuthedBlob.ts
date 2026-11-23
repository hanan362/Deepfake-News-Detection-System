import { useEffect, useState } from "react";
import { fetchBlob } from "@/services/api";

/** Fetches a protected file with the login token and gives back an object URL. `enabled` delays big downloads until asked for. */
export function useAuthedBlob(path: string | null, enabled = true) {
  const [state, setState] = useState<{ url: string | null; error: boolean }>({ url: null, error: false });
  useEffect(() => {
    if (!path || !enabled) return;
    const ctrl = new AbortController();
    let made: string | null = null;
    fetchBlob(path, ctrl.signal)
      .then((blob) => {
        made = URL.createObjectURL(blob);
        setState({ url: made, error: false });
      })
      .catch(() => !ctrl.signal.aborted && setState({ url: null, error: true }));
    return () => {
      ctrl.abort();
      if (made) URL.revokeObjectURL(made);
    };
  }, [path, enabled]);
  return state;
}
