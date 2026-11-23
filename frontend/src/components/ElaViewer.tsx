import { useState } from "react";
import { useAuthedImage } from "@/hooks/useAuthedImage";
import { Spinner } from "@/components/ui/Feedback";

type Mode = "original" | "map" | "blend";

export function ElaViewer({ analysisId }: { analysisId: number }) {
  const original = useAuthedImage(`/analysis/${analysisId}/image`);
  const map = useAuthedImage(`/analysis/${analysisId}/heatmap`);
  const [mode, setMode] = useState<Mode>("blend");
  const [blend, setBlend] = useState(55);

  const failed = original.error || map.error;
  const ready = original.url && map.url;
  const opacity = mode === "original" ? 0 : mode === "map" ? 1 : blend / 100;

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3" role="group" aria-label="Image view">
        {(["original", "blend", "map"] as Mode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            aria-pressed={mode === m}
            className={`btn btn-sm ${mode === m ? "btn-primary" : "btn-quiet"}`}
          >
            {m === "original" ? "Original" : m === "map" ? "Error level map" : "Blend"}
          </button>
        ))}
        {mode === "blend" && (
          <label className="flex items-center gap-2 text-sm text-ink-2">
            Map strength
            <input type="range" min={0} max={100} value={blend} onChange={(e) => setBlend(Number(e.target.value))} aria-label="Error level map strength" className="accent-cyan" />
          </label>
        )}
      </div>
      <div className="exhibit mt-4 flex min-h-64 items-center justify-center overflow-hidden p-2">
        {failed ? (
          <p className="p-8 text-sm text-ink-2">The image could not be loaded.</p>
        ) : !ready ? (
          <Spinner label="Loading image" />
        ) : (
          <div className="relative">
            <img src={original.url!} alt="The image you uploaded" className="block max-h-[28rem] max-w-full" />
            <img
              src={map.url!}
              alt="Error level analysis map of the uploaded image"
              className="absolute inset-0 h-full w-full transition-opacity"
              style={{ opacity, mixBlendMode: mode === "blend" ? "screen" : "normal" }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
