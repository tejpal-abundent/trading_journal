import { useEffect, useState } from "react";
import { api, Trade, TradeStatus } from "../api";
import TradeDetail from "./TradeDetail";

const GROUPS: { label: string; statuses: TradeStatus[] }[] = [
  { label: "Planned", statuses: ["planned"] },
  { label: "Open",    statuses: ["entered"] },
  { label: "Closed",  statuses: ["win", "loss", "breakeven"] },
  { label: "Skipped", statuses: ["skipped"] },
];

export default function TradeList() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [active, setActive] = useState<Trade | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setTrades(await api.listTrades());
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const groups = GROUPS.map(g => ({
    ...g,
    trades: trades.filter(t => g.statuses.includes(t.status)),
  })).filter(g => g.trades.length > 0);

  const onChanged = (t: Trade | null) => {
    if (t) setActive(t);
    load();
  };

  if (loading) return <p className="text-2 text-sm">Loading...</p>;
  if (trades.length === 0) return <p className="text-2 text-sm">No trades yet. Plan one!</p>;

  return (
    <div>
      {groups.map(g => (
        <div key={g.label} className="status-group">
          <h3>{g.label} ({g.trades.length})</h3>
          {g.trades.map(t => <TradeCard key={t.id} trade={t} onClick={() => setActive(t)} />)}
        </div>
      ))}
      {active && <TradeDetail trade={active} onClose={() => setActive(null)} onChanged={onChanged} />}
    </div>
  );
}

function TradeCard({ trade, onClick }: { trade: Trade; onClick: () => void }) {
  const border = trade.setup_score >= 85 ? "var(--green)"
              : trade.setup_score >= 70 ? "var(--yellow)"
              : trade.setup_score >= 55 ? "#D85A30" : "var(--red)";
  const statusColor = trade.status === "win" ? "tag-green"
                    : trade.status === "loss" ? "tag-red"
                    : trade.status === "breakeven" ? "tag-yellow"
                    : "tag-blue";
  return (
    <div className="card" style={{ borderLeft: `3px solid ${border}`, cursor: "pointer" }} onClick={onClick}>
      <div className="flex between center">
        <div className="flex gap-2 center wrap">
          <span className="font-500">{trade.pair}</span>
          <span className={`tag ${trade.direction === "LONG" ? "tag-green" : "tag-red"}`}>{trade.direction}</span>
          <span className="tag tag-blue">{trade.timeframe}</span>
          <span className={`tag ${statusColor}`}>{trade.status.toUpperCase()}</span>
          {trade.retroactive && <span className="tag" style={{ background: "var(--bg2)", color: "var(--text2)" }}>RETRO</span>}
        </div>
        <span className="font-500">{trade.setup_score}/100</span>
      </div>
      <div className="text-xs text-2 mt-2">
        {new Date(trade.created_at).toLocaleString()}
        {trade.risk_percent != null && <span> · risk {trade.risk_percent}%</span>}
        {trade.pnl != null && <span> · P/L ${trade.pnl}</span>}
      </div>
    </div>
  );
}
