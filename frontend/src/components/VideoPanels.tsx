import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { Film } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Feedback";
import { useAuthedBlob } from "@/hooks/useAuthedBlob";
import { useAuthedImage } from "@/hooks/useAuthedImage";
import type { Analysis, VideoDetails, VideoFrame } from "@/types/api";

const FLAG = 0.5;
const STATUS_TEXT: Record<VideoDetails["decision"]["status"], string> = {
  decided: "A call was made", undecided: "Score in the undecided range", not_enough_faces: "Too few frames with a face",
  not_calibrated: "No measured thresholds installed", classifier_unavailable: "Frame classifier not available",
};
const mmss = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

/** Facts about the video, how many frames could be used, and the rule that turned the scores into a verdict. */
export function VideoSummary({ d }: { d: VideoDetails }) {
  const t = d.temporal;
  const rows: [string, string][] = [
    ["Length", `${d.video.duration_seconds.toFixed(1)} s, ${d.video.width} x ${d.video.height} px, ${d.video.fps} frames per second`],
    ["Frames sampled", `${d.sampling.sampled}, evenly across the whole video`],
    ["Frames with a clear face", `${d.sampling.with_face} (at least ${d.sampling.min_face_frames} are needed for a call)`],
    ["Outcome", STATUS_TEXT[d.decision.status]],
    ...(t ? ([
      ["Video score", `${t.video_score.toFixed(3)} (${t.aggregator.replace(/_/g, " ")} of the frame scores)`],
      ["Frames scored 0.5 or higher", `${Math.round(t.flagged_share * 100)}%, longest run ${t.longest_flagged_run}`],
      ["Lowest and highest frame score", `${t.min.toFixed(2)} and ${t.max.toFixed(2)}`],
    ] as [string, string][]) : []),
    ...(d.decision.thresholds ? ([["Decision thresholds", `Fake from ${d.decision.thresholds.fake_min ?? "none"}, real up to ${d.decision.thresholds.real_max ?? "none"}`]] as [string, string][]) : []),
  ];
  return (
    <div data-testid="video-summary">
      <dl className="divide-y divide-line rounded-panel border border-line text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-6 px-4 py-2.5"><dt className="text-ink-2">{k}</dt><dd className="text-right">{v}</dd></div>
        ))}
      </dl>
      <p className="mt-4 max-w-prose text-sm text-ink-2"><span className="font-medium text-ink">The rule.</span> {d.decision.rule}</p>
      <p className="mt-2 max-w-prose rounded-control border border-warn/40 bg-warn/5 px-3 py-2.5 text-sm text-ink-2" data-testid="frame-based-note">{d.model.note}</p>
      {d.observations.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink-2 marker:text-ink-3">{d.observations.map((o) => <li key={o}>{o}</li>)}</ul>}
    </div>
  );
}

/** One dot per scored frame; a hollow dot on the baseline marks a frame where no face was found. Also available as a table. */
export function FrameScoreChart({ frames, duration, selected, onSelect }: { frames: VideoFrame[]; duration: number; selected: number | null; onSelect: (i: number) => void }) {
  const W = 640, H = 220, L = 40, R = 12, T = 12, B = 34;
  const x = (t: number) => L + (duration > 0 ? t / duration : 0) * (W - L - R);
  const y = (p: number) => T + (1 - p) * (H - T - B);
  const scored = frames.filter((f) => f.p_fake !== null);
  const path = scored.map((f, i) => `${i ? "L" : "M"}${x(f.t).toFixed(1)},${y(f.p_fake!).toFixed(1)}`).join(" ");
  const flagged = scored.filter((f) => f.p_fake! >= FLAG).length;
  return (
    <div data-testid="frame-chart">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`Fake score of ${scored.length} frames over ${duration.toFixed(0)} seconds. ${flagged} were scored 0.5 or higher.`}>
        {[0, 0.25, 0.5, 0.75, 1].map((p) => (
          <g key={p}>
            <line x1={L} x2={W - R} y1={y(p)} y2={y(p)} className={p === FLAG ? "stroke-warn" : "stroke-line"} strokeDasharray={p === FLAG ? "5 4" : undefined} strokeWidth={p === FLAG ? 1.25 : 1} />
            <text x={L - 8} y={y(p) + 4} textAnchor="end" className="fill-ink-3 text-[11px]">{p}</text>
          </g>
        ))}
        {[0, 0.5, 1].map((p) => (
          <text key={p} x={x(p * duration)} y={H - 12} textAnchor={p === 0 ? "start" : p === 1 ? "end" : "middle"} className="fill-ink-3 text-[11px]">{mmss(p * duration)}</text>
        ))}
        {path && <path d={path} fill="none" className="stroke-ink-3" strokeWidth={1.5} />}
        {frames.map((f, i) =>
          f.p_fake === null ? (
            <circle key={i} cx={x(f.t)} cy={y(0)} r={4} fill="none" className="stroke-ink-3" strokeWidth={1.5}><title>{`${mmss(f.t)}: no face found`}</title></circle>
          ) : (
            <circle key={i} cx={x(f.t)} cy={y(f.p_fake)} r={selected === i ? 7 : 5} strokeWidth={2} className={clsx("cursor-pointer stroke-paper", f.p_fake >= FLAG ? "fill-bad" : "fill-cyan")} onClick={() => onSelect(i)}>
              <title>{`${mmss(f.t)}: ${f.p_fake.toFixed(2)}`}</title>
            </circle>
          ),
        )}
      </svg>
      <p className="mt-1 flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-2">
        <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-bad align-middle" />Scored 0.5 or higher</span>
        <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-cyan align-middle" />Scored below 0.5</span>
        <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full border-2 border-ink-3 align-middle" />No face found</span>
        <span>Dashed line: 0.5</span>
      </p>
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-ink-2">Show the numbers as a table</summary>
        <table className="mt-2 w-full max-w-lg text-left text-sm">
          <thead className="text-ink-3"><tr><th className="py-1 pr-4 font-normal">Time</th><th className="py-1 pr-4 font-normal">Face</th><th className="py-1 pr-4 font-normal">Fake score</th><th className="py-1 font-normal">Sharpness</th></tr></thead>
          <tbody>{frames.map((f) => <tr key={f.index} className="border-t border-line"><td className="py-1 pr-4">{mmss(f.t)}</td><td className="py-1 pr-4">{f.face_found ? "yes" : "no"}</td><td className="py-1 pr-4">{f.p_fake === null ? "-" : f.p_fake.toFixed(3)}</td><td className="py-1">{f.sharpness === null ? "-" : f.sharpness.toFixed(0)}</td></tr>)}</tbody>
        </table>
      </details>
    </div>
  );
}

function Thumb({ analysisId, frame, index, active, onSelect }: { analysisId: number; frame: VideoFrame; index: number; active: boolean; onSelect: () => void }) {
  const img = useAuthedImage(frame.has_image ? `/analysis/${analysisId}/frames/${index}` : null);
  const flagged = frame.p_fake !== null && frame.p_fake >= FLAG;
  return (
    <button type="button" onClick={onSelect} aria-pressed={active} aria-label={`Frame at ${mmss(frame.t)}`}
      className={clsx("group overflow-hidden rounded-control border text-left", active ? "border-cyan ring-2 ring-cyan/40" : "border-line")}>
      <div className="flex aspect-video items-center justify-center bg-panel">
        {img.url ? <img src={img.url} alt="" className="h-full w-full object-cover" /> : img.error ? <span className="text-xs text-ink-3">unavailable</span> : <Spinner label="Loading frame" />}
      </div>
      <div className="flex items-center justify-between px-2 py-1 text-xs">
        <span className="text-ink-2">{mmss(frame.t)}</span>
        <span className={clsx(flagged ? "font-medium text-bad" : "text-ink-2")}>{frame.p_fake === null ? "no face" : frame.p_fake.toFixed(2)}</span>
      </div>
    </button>
  );
}

/** The uploaded video, loaded only when asked for (it can be large), so that a moment in the chart can be played. */
function VideoPlayer({ analysisId, seek, size }: { analysisId: number; seek: number | null; size?: string }) {
  const [wanted, setWanted] = useState(false);
  const blob = useAuthedBlob(`/analysis/${analysisId}/video`, wanted);
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    if (seek !== null && ref.current && blob.url) ref.current.currentTime = seek;
  }, [seek, blob.url]);
  if (!wanted) return <Button variant="quiet" onClick={() => setWanted(true)}><Film className="h-4 w-4" aria-hidden />Load the video to play it{size ? ` (${size})` : ""}</Button>;
  if (blob.error) return <p className="text-sm text-ink-2">The video could not be loaded.</p>;
  if (!blob.url) return <Spinner label="Loading the video" />;
  return <video ref={ref} src={blob.url} controls className="max-h-[26rem] max-w-full rounded-control bg-black" data-testid="video-player" aria-label="The video you uploaded" />;
}

export function VideoSection({ a }: { a: Analysis }) {
  const d = a.details as VideoDetails | null;
  const [selected, setSelected] = useState<number | null>(null);
  if (!d?.frames) return null;
  const pick = (i: number) => setSelected(i);
  const top = d.temporal?.suspicious_moments ?? [];
  return (
    <>
      <section className="mt-12" aria-labelledby="vid-h">
        <h2 id="vid-h" className="text-2xl">How the verdict was reached</h2>
        <div className="mt-4"><VideoSummary d={d} /></div>
      </section>

      <section className="mt-12" aria-labelledby="chart-h">
        <h2 id="chart-h" className="text-2xl">Frame scores over the video</h2>
        <p className="mt-2 max-w-prose text-ink-2">Each dot is one frame scored on its own. The score is the classifier's output, not the chance that the video is fake. Click a dot to see the frame.</p>
        <div className="mt-5"><FrameScoreChart frames={d.frames} duration={d.video.duration_seconds} selected={selected} onSelect={pick} /></div>
        {top.length > 0 && (
          <p className="mt-4 text-sm text-ink-2" data-testid="suspicious-moments">
            Highest-scoring moments:{" "}
            {top.map((m) => {
              const i = d.frames.findIndex((f) => f.t === m.t);
              return <button key={m.t} type="button" className="mr-3 underline underline-offset-2" onClick={() => pick(i)}>{mmss(m.t)} ({m.p_fake.toFixed(2)})</button>;
            })}
            <span className="text-ink-3">These are where the classifier scored highest, not proof of manipulation.</span>
          </p>
        )}
      </section>

      <section className="mt-12" aria-labelledby="frames-h">
        <h2 id="frames-h" className="text-2xl">Sampled frames</h2>
        <p className="mt-2 max-w-prose text-ink-2">The orange box is the face that was scored. Frames without a box had no clear face and were not scored.</p>
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6" data-testid="frame-grid">
          {d.frames.map((f, i) => <Thumb key={f.index} analysisId={a.id} frame={f} index={i} active={selected === i} onSelect={() => pick(i)} />)}
        </div>
        <div className="mt-6"><VideoPlayer analysisId={a.id} seek={selected === null ? null : d.frames[selected].t} /></div>
      </section>
    </>
  );
}
