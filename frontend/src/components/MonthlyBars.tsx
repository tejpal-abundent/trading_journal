import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { DashboardMonthly } from "../api";
import { formatCurrency } from "../lib/dashboard";

interface Props {
  data: DashboardMonthly[];
}

export default function MonthlyBars({ data }: Props) {
  const [mode, setMode] = useState<"close" | "split">("close");
  const key = mode === "close" ? "pnl_close_date" : "pnl_split";

  return (
    <div className="card">
      <div className="flex between center" style={{ marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Monthly P&L</h3>
        <div className="flex gap-1">
          <button
            className={`btn btn-sm ${mode === "close" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setMode("close")}
          >Close date</button>
          <button
            className={`btn btn-sm ${mode === "split" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setMode("split")}
          >Split by days</button>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(n) => formatCurrency(n)} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(v) => formatCurrency(Number(v))}
            contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)" }}
          />
          <Bar dataKey={key}>
            {data.map((d, i) => (
              <Cell key={i} fill={(d as any)[key] >= 0 ? "var(--green)" : "var(--red)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
