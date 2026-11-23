const ARABIC_SCRIPT = /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/g;

export function countWords(text: string): number {
  const t = text.trim();
  return t ? t.split(/\s+/).length : 0;
}

/** Letters Urdu uses that Arabic does not: the server's test for "this Arabic-script text is Urdu". */
const URDU_ONLY = /[ٹڈڑںےہھ]/g;

/** Mirrors the server's `looks_urdu`: Arabic-script text with enough Urdu-only letters. Roman Urdu cannot be detected. */
export function looksUrdu(text: string): boolean {
  if (!looksArabicScript(text)) return false;
  const letters = text.match(/\p{L}/gu)?.length ?? 0;
  return letters > 0 && (text.match(URDU_ONLY)?.length ?? 0) / letters >= 0.02;
}

/** Mirrors the server's script check: mostly Arabic-script letters means Urdu, Arabic or Persian text. */
export function looksArabicScript(text: string): boolean {
  const letters = text.match(/\p{L}/gu)?.length ?? 0;
  if (letters === 0) return false;
  return (text.match(ARABIC_SCRIPT)?.length ?? 0) / letters > 0.3;
}
