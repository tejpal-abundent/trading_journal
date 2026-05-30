import { formatCurrency, formatPercent } from "../lib/dashboard";

interface Props {
  label: string;
  primary: number;
  trades: number;
  winRate: number;
  unit?: "$" | "count";
}

export default function KPICard({ label, primary, trades, winRate, unit = "$" }: Props) {
  const color = unit === "$" ? (primary > 0 ? "var(--green)" : primary < 0 ? "var(--red)" : "var(--text2)") : "var(--text)";
  const value = unit === "$" ? formatCurrency(primary) : primary.toString();
  return (
    <div className="card" style={{ minWidth: 160 }}>
      <div className="text-xs text-2">{label}</div>
      <div className="font-500" style={{ fontSize: 28, color, marginTop: 4 }}>{value}</div>
      {unit === "$" && (
        <div className="text-xs text-2" style={{ marginTop: 4 }}>
          {trades} trade{trades === 1 ? "" : "s"} · {formatPercent(winRate)} win
        </div>
      )}
    </div>
  );
}
