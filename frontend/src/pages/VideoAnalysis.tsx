import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Film, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { StatusPill } from "@/components/ui/StatusPill";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useModels } from "@/hooks/useModels";
import { useSlowFlag } from "@/hooks/useSlowFlag";
import { SlowNotice } from "@/components/SlowNotice";
import { api, ApiError } from "@/services/api";
import { formatBytes, validateVideoFile } from "@/utils/files";

export default function VideoAnalysis() {
  useDocumentTitle("Analyse a video");
  const toast = useToast();
  const navigate = useNavigate();
  const { data: models, byModule } = useModels();
  const entry = byModule("video");
  const maxMb = models?.limits.max_video_mb ?? 100;
  const maxSeconds = models?.limits.max_video_seconds ?? 180;
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const slow = useSlowFlag(busy, 20_000);

  const choose = useCallback((f: File | undefined | null) => {
    if (!f) return;
    const problem = validateVideoFile(f, maxMb);
    setError(problem);
    setFile(problem ? null : f);
  }, [maxMb]);

  async function analyse() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.analysis.video(file);
      toast.success("Analysis saved.");
      navigate(`/analysis/${result.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1>Analyse a video</h1>
          {entry && <StatusPill status={entry.status} />}
        </div>
        <p className="mt-3 text-ink-2">Upload a short clip of a person speaking. Frames are sampled across the whole video, the face in each is scored, and the scores are summarised over time. A video is never judged from a single frame.</p>
        {entry && entry.status !== "experimental" && <p className="mt-4 rounded-control border border-warn/40 bg-warn/5 px-3 py-2.5 text-sm text-ink-2" data-testid="video-limited">{entry.description}</p>}
        {entry?.status === "unavailable" && <p className="mt-3 text-sm text-ink-2">Video analysis cannot run on this server: {entry.description}</p>}

        <div className="mt-8 space-y-5">
          <input ref={input} type="file" accept="video/mp4,video/quicktime,video/webm,video/x-msvideo,.mp4,.mov,.webm,.avi" className="sr-only" aria-label="Choose a video file" onChange={(e) => { choose(e.target.files?.[0]); e.target.value = ""; }} />
          {!file ? (
            <button type="button" onClick={() => input.current?.click()} className="exhibit flex min-h-48 w-full cursor-pointer flex-col items-center justify-center gap-2 px-6 py-10 text-center">
              <Film className="h-8 w-8 text-cyan" aria-hidden />
              <span className="font-display text-lg">Choose a video</span>
              <span className="text-sm text-ink-2">MP4, MOV, WebM or AVI, up to {maxMb} MB and {Math.round(maxSeconds / 60)} minutes</span>
            </button>
          ) : (
            <div className="exhibit flex items-start gap-4 p-4">
              <Film className="mt-1 h-6 w-6 text-cyan" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium" data-testid="file-name">{file.name}</p>
                <p className="mt-1 text-sm text-ink-2">{formatBytes(file.size)}</p>
                <Button variant="ghost" size="sm" className="mt-2" onClick={() => { setFile(null); setError(null); }} disabled={busy}><X className="h-4 w-4" aria-hidden />Remove</Button>
              </div>
            </div>
          )}
          {error && <p className="error-text" role="alert" data-testid="video-error">{error}</p>}
          {busy && <p className="text-sm text-ink-2" role="status">Uploading and analysing. A longer video can take up to a minute.</p>}
          <SlowNotice show={slow} what="video analysis" />
          <div className="flex justify-end">
            <Button onClick={analyse} busy={busy} disabled={!file || entry?.status === "unavailable"}><Film className="h-4 w-4" aria-hidden />Analyse video</Button>
          </div>
        </div>
      </div>

      <aside className="space-y-6 lg:pt-[5.5rem]" aria-label="What to expect">
        <section className="panel panel-pad">
          <h2 className="text-xl">What you get</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>A score for each sampled frame, shown over time, with the face that was scored.</li>
            <li>A verdict only when enough frames show a clear face and the overall score is clear.</li>
            <li>The video and its frames, kept in your account until you delete the analysis.</li>
          </ul>
        </section>
        <section className="panel panel-pad">
          <h2 className="text-xl">What it cannot do</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>Learn motion or timing problems: each frame is judged alone.</li>
            <li>Analyse the sound, or say whether the footage is used truthfully.</li>
            <li>Work reliably on small, blurred or turned faces, or on methods it was not tested on.</li>
          </ul>
        </section>
      </aside>
    </div>
  );
}
