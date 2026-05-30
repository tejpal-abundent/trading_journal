import { DashboardHeatCell } from "../api";
import { formatCurrency, maxAbsOf } from "../lib/dashboard";

export default function DailyHeatmap({ data }: { data: DashboardHeatCell[] }) {
  const maxAbs = maxAbsOf(data, d => d.pnl);
  const weeks: DashboardHeatCell[][] = [];
  for (let i = 0; i < data.length; i += 7) weeks.push(data.slice(i, i + 7));

  const colorFor = (pnl: number) => {
    if (pnl === 0 || maxAbs === 0) return "var(--bg2)";
    return pnl > 0 ? "var(--green)" : "var(--red)";
  };
  const opacityFor = (pnl: number) => {
    if (pnl === 0 || maxAbs === 0) return 1;
    return 0.3 + 0.7 * Math.min(1, Math.abs(pnl) / maxAbs);
  };

  return (
    <div className="card">
      <h3 style={{ margin: 0, marginBottom: 8 }}>Daily activity (90d)</h3>
      <div style={{ display: "flex", gap: 3 }}>
        {weeks.map((week, wi) => (
          <div key={wi} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {week.map((d) => (
              <div
                key={d.date}
                title={`${d.date}: ${formatCurrency(d.pnl)} · ${d.trades} trade${d.trades === 1 ? "" : "s"}`}
                style={{
                  width: 16, height: 16, borderRadius: 3,
                  background: colorFor(d.pnl),
                  opacity: opacityFor(d.pnl),
                }}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
