interface Item {
  label: string;
  value: number;
}

/** A labelled share list: value at the bar tip, thin bar with a rounded end, the name always written out. */
export function HorizontalBars({ items, emptyText = "Nothing to show yet." }: { items: Item[]; emptyText?: string }) {
    const total = items.reduce((s, i) => s + i.value, 0);
  if (items.length === 0 || total === 0) return <p className="text-sm text-ink-2">{emptyText}</p>;
  return (
    <ul className="space-y-3.5">
      {items.map((i) => (
        <li key={i.label}>
          <div className="mb-1.5 flex items-baseline justify-between text-sm">
            <span>{i.label}</span>
            <span className="tabular-nums text-ink-2">{i.value} <span className="text-ink-3">({Math.round((i.value / total) * 100)}%)</span></span>
          </div>
          <div className="h-2 rounded-full bg-raised" role="img" aria-label={`${i.label}: ${i.value} of ${total}`}>
            <div className="h-full rounded-r-[4px] rounded-l-sm bg-link" style={{ width: `${(i.value / total) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
