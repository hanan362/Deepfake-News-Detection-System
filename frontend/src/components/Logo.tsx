/** Three lines of text, one of them marked: a story being read and checked. */
export function LogoMark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="9" fill="#141A3C" />
      <rect x="7" y="8" width="18" height="3" rx="1.5" fill="#C9CEE8" />
      <rect x="5.5" y="14.2" width="21" height="5.4" rx="1.4" fill="#FFD60A" />
      <rect x="8.5" y="15.9" width="15" height="2" rx="1" fill="#141A3C" />
      <rect x="7" y="22.5" width="12" height="3" rx="1.5" fill="#C9CEE8" />
    </svg>
  );
}

export function Wordmark({ onDark = false }: { onDark?: boolean }) {
  return (
    <span className="flex shrink-0 items-center gap-2.5 whitespace-nowrap">
      <LogoMark />
      <span className="leading-none">
        <span className={`block font-display text-[1.1rem] font-bold tracking-tight ${onDark ? "text-white" : "text-ink"}`}>Deepfake News</span>
        <span className={`mt-1 block text-[0.74rem] font-medium ${onDark ? "text-rail-dim" : "text-ink-2"}`}>Detection System</span>
      </span>
    </span>
  );
}
