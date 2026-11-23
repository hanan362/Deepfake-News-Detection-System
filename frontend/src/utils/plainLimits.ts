import type { Analysis } from "@/types/api";

const TEXT = "This reads how a text is written. It does not check whether the claims are true, so a true story can come out Unverified and a convincing lie can come out Likely Real. It was tested on limited collections of articles and can be wrong, most of all on short texts, posts and subjects unlike the articles it learned from.";

/** What every reader is told about the limits of a result, in plain words. The measured numbers behind them are for administrators. */
export function plainLimits(a: Pick<Analysis, "analysis_type">): string[] {
  switch (a.analysis_type) {
    case "image":
      return ["These are signs, not a verdict. A photo can be edited or generated without leaving any trace, and an honest photo can show traces, for example from being saved again or compressed."];
    case "video":
      return ["Each frame is judged on its own and only faces are looked at. Face swaps made with newer methods may go unnoticed, so a clean result does not mean the video is genuine."];
    case "multimodal":
      return ["The picture and the caption are compared by a general-purpose model that is wrong about some matching pairs. It cannot tell whether either of them is true.", TEXT];
    case "evidence":
      return ["The answer rests only on the sources listed under each claim. Not finding evidence does not mean the claim is false, and a source can be wrong too."];
    default:
      return [TEXT];
  }
}
