import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { DashboardWeekly } from "../api";
import { formatCurrency } from "../lib/dashboard";

export default function WeeklyBars({ data }: { data: DashboardWeekly[] }) {
  return (
    <div className="card">
      <h3 style={{ margin: 0, marginBottom: 8 }}>Weekly P&L (last 4)</h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data}>
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(n) => formatCurrency(n)} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(v) => formatCurrency(Number(v))}
            contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
          />
          <Bar dataKey="pnl">
            {data.map((d, i) => (
              <Cell key={i} fill={d.pnl >= 0 ? "var(--green)" : "var(--red)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
