import type { TermWeight } from "@/types/api";

export interface Segment {
  text: string;
  tone: "fake" | "real" | null;
}

/**
 * Mark the words of the submitted text that the model's explanation named. A listed term can be one word or two
 * ("city council"), so every word of every listed term is marked. A word that appears in terms of both kinds takes the
 * side with the larger weight.
 */
export function highlightSegments(text: string, toward_fake: TermWeight[], toward_real: TermWeight[]): Segment[] {
  const strength = new Map<string, { tone: "fake" | "real"; weight: number }>();
  const add = (terms: TermWeight[], tone: "fake" | "real") => {
    for (const { term, weight } of terms) {
      for (const word of term.toLowerCase().split(/\s+/)) {
        const current = strength.get(word);
        if (!current || Math.abs(weight) > current.weight) strength.set(word, { tone, weight: Math.abs(weight) });
      }
    }
  };
  add(toward_fake, "fake");
  add(toward_real, "real");

  const segments: Segment[] = [];
  for (const part of text.split(/(\b[\p{L}\p{N}']{2,}\b)/u)) {
    if (!part) continue;
    const hit = strength.get(part.toLowerCase());
    const last = segments[segments.length - 1];
    const tone = hit ? hit.tone : null;
    if (last && last.tone === tone && tone === null) last.text += part;
    else segments.push({ text: part, tone });
  }
  return segments;
}
