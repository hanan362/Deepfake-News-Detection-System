import type { ReactNode } from "react";
import clsx from "clsx";
import { CircleHelp, ScanSearch, ShieldAlert, ShieldCheck, type LucideIcon } from "lucide-react";
import type { Analysis } from "@/types/api";
import { verdictBand, type Band } from "@/utils/format";

const BAND_CLASS: Record<Band, string> = { real: "band-real", fake: "band-fake", unsure: "band-unsure", flag: "band-flag" };
const ICON: Record<string, LucideIcon> = { "Likely Fake": ShieldAlert, "Likely Real": ShieldCheck, Unverified: CircleHelp, "Indicators Only": ScanSearch, Supported: ShieldCheck, "Mismatch Flagged": ShieldAlert, Contradicted: ShieldAlert, "Mixed Evidence": CircleHelp, "Insufficient Evidence": CircleHelp };

/** The plain-language sentence that goes with a verdict. It always says what the verdict does not mean. */
export function rulingLine(a: Pick<Analysis, "verdict" | "details" | "analysis_type">): string {
  const d = a.details;
  switch (a.verdict) {
    case "Likely Fake":
      if (a.analysis_type === "video") return "The frame scores are in the range this classifier gave to face-swap videos in its tests. It was tested on small samples and judges each frame alone, so this is not proof of manipulation.";
      return "The writing resembles articles that were labelled fake in the training data. This is not proof that any claim is false.";
    case "Likely Real":
      if (a.analysis_type === "video") return "The frame scores are in the range this classifier gave to genuine videos in its tests. It cannot see manipulations it was not tested on, so this does not confirm the video is authentic.";
      if (d?.reason === "published_by_listed_outlet") return "The page is on the website of a well-known news organisation, so it was published by them. That shows who published it, not that what it says is accurate, and the writing-style reading alone could not decide.";
      if (d?.reason === "corroborated") return "A well-known news organisation published a headline that says the same. That shows the story was reported, not that it is accurate, and only the headline was compared, not the article.";
      return "The writing resembles articles that were labelled real in the training data. This does not confirm that any claim is true.";
    case "Unverified":
      if (a.analysis_type === "video") return d?.decision?.status === "not_enough_faces" ? "Too few frames show a clear face, so no call is made. A video is never judged from a single frame." : "The overall score is in the range where this classifier was not reliable, so no call is made.";
      if (a.analysis_type === "multimodal") return d?.message ?? "Nothing in this pair could be judged by the text model, so no call is made.";
      if (d?.reason === "headline_text_mismatch") return d.message ?? "The headline and the text under it do not match, so no call is made.";
      if (d?.reason === "signals_differ" || d?.reason === "disputed") return d.message ?? "The two readings disagree, so no call is made.";
      if (d?.reason === "too_short" || d?.reason === "unsupported_language" || d?.reason === "article_not_readable" || d?.reason === "declared_satire") return d.message ?? "The model cannot assess this input.";
      return "The model does not lean clearly either way, so it makes no call. Treat the story as unchecked.";
    case "Mismatch Flagged":
      return "The image and the text clearly do not describe the same thing, according to a similarity check that is wrong about one in ten matching pairs. This is a flag to look closer, not proof that either is false.";
    case "Supported":
      return "Retrieved evidence supports the claim. This is only as reliable as the sources searched; it is not a guarantee that the claim is true.";
    case "Contradicted":
      return "Retrieved evidence contradicts the claim. This is only as reliable as the sources searched; check them yourself.";
    case "Mixed Evidence":
      return "Some evidence supports the claim and some contradicts it. Read each source below.";
    case "Insufficient Evidence":
      return "Nothing found was clear enough to support or contradict the claim. This does not mean the claim is false.";
    case "Indicators Only":
      if (a.analysis_type === "video") return "These are measurements and per-frame scores, not a verdict: this build has no measured decision rule for the frame classifier.";
      return "These are measurements, not a verdict. They cannot show whether an image is authentic, edited or AI-generated.";
    default:
      return "";
  }
}

/** The answer, as a band in the colour of the verdict. It always carries the sentence that says what the verdict does not mean. */
export function VerdictRuling({ analysis, size = "lg", children }: { analysis: Pick<Analysis, "verdict" | "details" | "analysis_type">; size?: "lg" | "md"; children?: ReactNode }) {
  const band = verdictBand(analysis.verdict);
  const Icon = ICON[analysis.verdict] ?? CircleHelp;
  return (
    <div className={clsx("band rounded-panel", BAND_CLASS[band], size === "lg" ? "px-6 py-8 sm:px-10 sm:py-10" : "px-5 py-5")}>
      <div className="flex items-center gap-4">
        <Icon className={size === "lg" ? "h-10 w-10 shrink-0 sm:h-12 sm:w-12" : "h-7 w-7 shrink-0"} aria-hidden />
        <p className={clsx("font-display font-extrabold leading-none tracking-tight", size === "lg" ? "text-[clamp(2.4rem,7vw,4.4rem)]" : "text-3xl")} data-testid="verdict">
          {analysis.verdict}
        </p>
      </div>
      <p className={clsx("max-w-2xl text-white/95", size === "lg" ? "mt-5 text-[1.05rem] leading-relaxed" : "mt-3 text-[0.95rem]")}>{rulingLine(analysis)}</p>
      {children}
    </div>
  );
}

/** A small solid tag in the colour of the verdict, for lists. The words carry the meaning as well as the colour. */
export function VerdictBadge({ verdict }: { verdict: string }) {
  const band = verdictBand(verdict);
  const Icon = ICON[verdict] ?? CircleHelp;
  return (
    <span className={clsx("pill border-transparent text-white", BAND_CLASS[band])}>
      <Icon className="h-3 w-3" aria-hidden />
      {verdict}
    </span>
  );
}
