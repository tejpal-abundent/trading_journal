import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { DashboardEquityPoint } from "../api";
import { formatCurrency } from "../lib/dashboard";

export default function EquityCurve({ data }: { data: DashboardEquityPoint[] }) {
  if (data.length === 0) {
    return (
      <div className="card">
        <h3 style={{ margin: 0, marginBottom: 8 }}>Equity curve</h3>
        <div className="text-2 text-sm">No closed trades yet.</div>
      </div>
    );
  }
  return (
    <div className="card">
      <h3 style={{ margin: 0, marginBottom: 8 }}>Equity curve</h3>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(n) => formatCurrency(n)} tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
          <Tooltip
            formatter={(v) => formatCurrency(Number(v))}
            contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
          />
          <Line type="monotone" dataKey="cumulative_pnl" stroke="var(--blue)" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
