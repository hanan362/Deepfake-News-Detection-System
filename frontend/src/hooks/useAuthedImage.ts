import { useEffect, useState } from "react";
import { fetchBlob } from "@/services/api";

/** Load an image that sits behind authentication. <img src> cannot send a bearer token, so fetch it and use a blob URL. */
export function useAuthedImage(path: string | null): { url: string | null; error: boolean } {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!path) {
      setUrl(null);
      return;
    }
    const controller = new AbortController();
    let objectUrl: string | null = null;
    setError(false);
    fetchBlob(path, controller.signal)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch((e) => {
        if ((e as Error).name !== "AbortError") setError(true);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  return { url, error };
}
