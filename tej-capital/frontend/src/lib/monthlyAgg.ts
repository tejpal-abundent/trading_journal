import type { EquityPoint } from "../hooks/useMetrics";

export type MonthAgg = { year: number; month: number; value: number; n: number };

/** Compounds a daily equity-point series into calendar-month returns.
 * Months absent from the input never appear here — callers render those
 * as blank cells (R3: no trading month is never "0%"). */
export function aggregateMonths(points: EquityPoint[]): MonthAgg[] {
  const byMonth = new Map<string, { compounded: number; n: number }>();
  for (const p of points) {
    const key = p.date.slice(0, 7);
    const cur = byMonth.get(key) ?? { compounded: 1, n: 0 };
    cur.compounded *= 1 + p.return;
    cur.n += 1;
    byMonth.set(key, cur);
  }
  return Array.from(byMonth.entries()).map(([key, v]) => {
    const [y, m] = key.split("-").map(Number);
    return { year: y, month: m, value: v.compounded - 1, n: v.n };
  });
}
