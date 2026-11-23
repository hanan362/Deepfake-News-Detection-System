import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatDay } from "@/utils/format";

interface Point {
  date: string;
  count: number;
}

function Tip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-panel border border-line bg-raised px-3 py-2 text-sm shadow-lg shadow-black/20">
      <p className="text-ink-2">{formatDay(p.date)}</p>
      <p className="font-medium">{p.count} {p.count === 1 ? "analysis" : "analyses"}</p>
    </div>
  );
}

/** Columns per day: one series, so no legend; thin marks with rounded tops, hairline grid, tooltip and a table view. */
export function ActivityChart({ data, label = "Analyses per day" }: { data: Point[]; label?: string }) {
  const [table, setTable] = useState(false);
  const total = data.reduce((s, d) => s + d.count, 0);
  const max = Math.max(1, ...data.map((d) => d.count));

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-sm text-ink-2">{label}, last {data.length} days</p>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setTable((t) => !t)} aria-pressed={table}>
          {table ? "Show chart" : "View as table"}
        </button>
      </div>
      {table ? (
        <div className="max-h-64 overflow-auto rounded-panel border border-line">
          <table>
            <thead><tr><th className="th">Date</th><th className="th text-right">Analyses</th></tr></thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.date} className="row"><td className="td py-2">{formatDay(d.date)}</td><td className="td py-2 text-right tabular-nums">{d.count}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div role="img" aria-label={`${label}: ${total} in total over the last ${data.length} days`} className="h-56">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: -18 }} barCategoryGap={6}>
              <CartesianGrid vertical={false} stroke="rgb(var(--line))" strokeWidth={1} />
              <XAxis dataKey="date" tickFormatter={formatDay} tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={28} tick={{ fill: "rgb(var(--ink-3))", fontSize: 12 }} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} domain={[0, Math.max(4, max)]} tickCount={5} tick={{ fill: "rgb(var(--ink-3))", fontSize: 12 }} />
              <Tooltip cursor={{ fill: "rgb(var(--raised))" }} content={<Tip />} />
              <Bar dataKey="count" fill="rgb(var(--link))" maxBarSize={22} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
