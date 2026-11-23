import { useEffect } from "react";

export function useDocumentTitle(title: string) {
  useEffect(() => {
    const previous = document.title;
    document.title = `${title} - Deepfake News Detection System`;
    return () => {
      document.title = previous;
    };
  }, [title]);
}
