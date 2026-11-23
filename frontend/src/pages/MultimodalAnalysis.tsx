import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ImagePlus, Layers, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { TextArea, TextInput } from "@/components/ui/Field";
import { StatusPill } from "@/components/ui/StatusPill";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useModels } from "@/hooks/useModels";
import { useSlowFlag } from "@/hooks/useSlowFlag";
import { SlowNotice } from "@/components/SlowNotice";
import { api, ApiError } from "@/services/api";
import { formatBytes, validateImageFile } from "@/utils/files";

export default function MultimodalAnalysis() {
  useDocumentTitle("Analyse an image with its text");
  const toast = useToast();
  const navigate = useNavigate();
  const { data: models, byModule } = useModels();
  const entry = byModule("multimodal");
  const maxMb = models?.limits.max_image_mb ?? 10;
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [headline, setHeadline] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const slow = useSlowFlag(busy, 12_000);

  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const choose = useCallback((f: File | undefined | null) => {
    if (!f) return;
    const problem = validateImageFile(f, maxMb);
    setError(problem);
    setFile(problem ? null : f);
  }, [maxMb]);

  const hasInput = Boolean(file || text.trim() || headline.trim());

  async function analyse() {
    if (!hasInput) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.analysis.multimodal({ file, text, headline });
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
          <h1>Analyse an image with its text</h1>
          {entry && <StatusPill status={entry.status} />}
        </div>
        <p className="mt-3 text-ink-2">Give a photo and the headline or article that goes with it. Each part is analysed on its own, and a check shows whether the image and the text describe the same thing. Either part can be left out.</p>
        {entry?.status === "heuristic" && <p className="mt-4 rounded-control border border-warn/40 bg-warn/5 px-3 py-2.5 text-sm text-ink-2" data-testid="clip-off">{entry.description}</p>}

        <div className="mt-8 space-y-5">
          <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" aria-label="Choose an image file" onChange={(e) => { choose(e.target.files?.[0]); e.target.value = ""; }} />
          {!file ? (
            <button type="button" onClick={() => input.current?.click()} className="exhibit flex min-h-40 w-full cursor-pointer flex-col items-center justify-center gap-2 px-6 py-8 text-center">
              <ImagePlus className="h-7 w-7 text-cyan" aria-hidden />
              <span className="font-display text-lg">Choose an image <span className="text-ink-3">(optional)</span></span>
              <span className="text-sm text-ink-2">JPEG, PNG or WEBP, up to {maxMb} MB</span>
            </button>
          ) : (
            <div className="exhibit flex items-start gap-4 p-4">
              {preview && <img src={preview} alt="Preview of the chosen image" className="h-32 w-32 rounded-exhibit object-cover" />}
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium" data-testid="file-name">{file.name}</p>
                <p className="mt-1 text-sm text-ink-2">{formatBytes(file.size)}</p>
                <Button variant="ghost" size="sm" className="mt-2" onClick={() => { setFile(null); setError(null); }}><X className="h-4 w-4" aria-hidden />Remove</Button>
              </div>
            </div>
          )}
          <TextInput label="Headline or caption" value={headline} onChange={(e) => setHeadline(e.target.value)} maxLength={500} optional hint="This is the text the image is compared with." />
          <TextArea label="Article text" value={text} onChange={(e) => setText(e.target.value)} rows={8} optional hint="At least 60 words for the text model to judge the writing. Shorter text is still compared with the image." />
          {error && <p className="error-text" role="alert" data-testid="multimodal-error">{error}</p>}
          <SlowNotice show={slow} what="the image-and-text check" />
          <div className="flex justify-end">
            <Button onClick={analyse} busy={busy} disabled={!hasInput}><Layers className="h-4 w-4" aria-hidden />Analyse together</Button>
          </div>
        </div>
      </div>

      <aside className="space-y-6 lg:pt-[5.5rem]" aria-label="What to expect">
        <section className="panel panel-pad">
          <h2 className="text-xl">What you get</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>The text model's reading of the article, if it is long enough.</li>
            <li>Forensic indicators for the image. No verdict from these.</li>
            <li>A match check between image and text, and the exact rule that combines everything.</li>
          </ul>
        </section>
        <section className="panel panel-pad">
          <h2 className="text-xl">What it cannot do</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>Tell whether a photo is from the event the text describes.</li>
            <li>Judge a match reliably on news photos: it was measured on everyday photos, and still flags about one matching pair in ten.</li>
          </ul>
        </section>
      </aside>
    </div>
  );
}
