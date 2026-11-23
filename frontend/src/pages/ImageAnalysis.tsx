import { useCallback, useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ImagePlus, ScanSearch, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { useModels } from "@/hooks/useModels";
import { api, ApiError } from "@/services/api";
import { formatBytes, validateImageFile } from "@/utils/files";

export default function ImageAnalysis() {
  useDocumentTitle("Inspect an image");
  const toast = useToast();
  const navigate = useNavigate();
  const { data: models } = useModels();
  const maxMb = models?.limits.max_image_mb ?? 10;
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);

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

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    choose(e.dataTransfer.files?.[0]);
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      input.current?.click();
    }
  };

  async function analyse() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.analysis.image(file);
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
        <h1>Inspect an image</h1>
        <p className="mt-3 text-ink-2">Upload a photo from a story. You get forensic measurements and an error level map to look at. You do not get a verdict, because these checks cannot give a reliable one.</p>

        <div className="mt-8">
          <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" aria-label="Choose an image file" onChange={(e) => { choose(e.target.files?.[0]); e.target.value = ""; }} />
          {!file ? (
            <div
              role="button"
              tabIndex={0}
              onClick={() => input.current?.click()}
              onKeyDown={onKey}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={`exhibit flex min-h-64 cursor-pointer flex-col items-center justify-center gap-3 px-6 py-10 text-center transition-colors ${dragging ? "!bg-link/10" : ""}`}
              aria-label="Upload area. Press Enter to choose an image."
            >
              <ImagePlus className="h-8 w-8 text-cyan" aria-hidden />
              <p className="font-display text-xl">Drop an image here, or choose one</p>
              <p className="text-sm text-ink-2">JPEG, PNG or WEBP, up to {maxMb} MB</p>
            </div>
          ) : (
            <div className="exhibit p-4">
              <div className="flex items-start gap-4">
                {preview && <img src={preview} alt="Preview of the chosen image" className="h-40 w-40 rounded-exhibit object-cover" />}
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium" data-testid="file-name">{file.name}</p>
                  <p className="mt-1 text-sm text-ink-2">{formatBytes(file.size)}, {file.type || "image"}</p>
                  <Button variant="ghost" size="sm" className="mt-3" onClick={() => { setFile(null); setError(null); }}><X className="h-4 w-4" aria-hidden />Remove</Button>
                </div>
              </div>
            </div>
          )}
          {error && <p className="error-text" role="alert">{error}</p>}
          <div className="mt-6 flex justify-end">
            <Button onClick={analyse} busy={busy} disabled={!file}><ScanSearch className="h-4 w-4" aria-hidden />Inspect image</Button>
          </div>
        </div>
      </div>

      <aside className="space-y-6 lg:pt-[5.5rem]" aria-label="What to expect">
        <section className="panel panel-pad">
          <h2 className="text-xl">What you get</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-ink-2 marker:text-ink-3">
            <li>Error level analysis: how much each area changes when the image is saved again.</li>
            <li>The camera and software metadata the file carries, if any.</li>
            <li>Plain observations, each with its caveat.</li>
          </ul>
        </section>
        <section className="panel panel-pad">
          <h2 className="text-xl">Your file</h2>
          <p className="mt-3 text-sm text-ink-2">It is checked by its contents, stored privately under a random name, and removed when you delete the analysis from your history.</p>
        </section>
      </aside>
    </div>
  );
}
