/**
 * Frontend-only helpers for the dashboard. The heavy math lives server-side
 * in backend/dashboard.py; this is just formatting & color helpers.
 */

export function formatCurrency(n: number): string {
  const abs = Math.abs(n);
  const formatted = abs.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: abs >= 100 ? 0 : 2,
  });
  return n < 0 ? `-$${formatted}` : `$${formatted}`;
}

export function formatPercent(n: number): string {
  return `${Math.round(n * 100)}%`;
}

/**
 * Heatmap cell color from a P&L value. Returns a CSS color from the project's
 * existing CSS-variable palette (--green, --red), with opacity scaled by magnitude.
 * Zero/missing days get a neutral gray (--bg2).
 */
export function heatColor(pnl: number, maxAbs: number): string {
  if (pnl === 0 || maxAbs === 0) return "var(--bg2)";
  if (pnl > 0) return "var(--green)";
  return "var(--red)";
}

export function maxAbsOf<T>(items: T[], fn: (t: T) => number): number {
  return items.reduce((m, t) => Math.max(m, Math.abs(fn(t))), 0);
}
