export function computeRisk(
  entry: number | null,
  stop: number | null,
  positionSize: number | null,
  accountSize: number | null,
): { risk_dollars: number | null; risk_percent: number | null } {
  if (entry == null || stop == null || positionSize == null || accountSize == null) {
    return { risk_dollars: null, risk_percent: null };
  }
  const dollars = Math.round(Math.abs(entry - stop) * positionSize * 10000) / 10000;
  if (accountSize === 0) return { risk_dollars: dollars, risk_percent: null };
  const pct = Math.round((dollars / accountSize) * 100 * 10000) / 10000;
  return { risk_dollars: dollars, risk_percent: pct };
}
