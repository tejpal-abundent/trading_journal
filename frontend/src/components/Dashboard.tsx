import { useEffect, useState } from "react";
import { api, Dashboard } from "../api";
import KPICard from "./KPICard";
import MonthlyBars from "./MonthlyBars";
import WeeklyBars from "./WeeklyBars";
import DailyHeatmap from "./DailyHeatmap";
import EquityCurve from "./EquityCurve";

export default function DashboardPage() {
  const [d, setD] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDashboard().then(setD).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-2 text-sm">Loading dashboard…</div>;
  if (!d) return <div className="text-2 text-sm">Dashboard unavailable.</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="flex gap-2 wrap">
        <KPICard label={d.this_week.label}  primary={d.this_week.pnl}  trades={d.this_week.trades}  winRate={d.this_week.win_rate} />
        <KPICard label={d.this_month.label} primary={d.this_month.pnl} trades={d.this_month.trades} winRate={d.this_month.win_rate} />
        <KPICard label={d.ytd.label}        primary={d.ytd.pnl}        trades={d.ytd.trades}        winRate={d.ytd.win_rate} />
        <KPICard label="Open trades" primary={d.open_trades.count} trades={0} winRate={0} unit="count" />
      </div>
      <EquityCurve data={d.equity_curve} />
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
        <MonthlyBars data={d.monthly} />
        <WeeklyBars data={d.weekly} />
      </div>
      <DailyHeatmap data={d.daily_heatmap} />
    </div>
  );
}
