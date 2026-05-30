import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Trade } from "../api";

export default function TradeRail() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.listTrades().then(setTrades).finally(() => setLoading(false));
  }, []);

  const open   = trades.filter(t => t.status === "entered");
  const closed = trades.filter(t => ["win", "loss", "breakeven"].includes(t.status));

  return (
    <aside style={{
      width: 240, minWidth: 240, borderLeft: "1px solid var(--border)",
      padding: 12, overflowY: "auto", maxHeight: "calc(100vh - 64px)",
    }}>
      <Section title={`Open (${open.length})`} trades={open}   onClick={t => navigate(`/trade/${t.id}`)} />
      <div style={{ height: 16 }} />
      <Section title={`Closed (${closed.length})`} trades={closed} onClick={t => navigate(`/trade/${t.id}`)} />
      {loading && <div className="text-xs text-2" style={{ marginTop: 8 }}>Loading…</div>}
      {!loading && trades.length === 0 && (
        <div className="text-xs text-2" style={{ marginTop: 8 }}>No trades yet.</div>
      )}
    </aside>
  );
}

function Section({ title, trades, onClick }: { title: string; trades: Trade[]; onClick: (t: Trade) => void }) {
  return (
    <div>
      <div className="text-xs text-2" style={{ marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {trades.map(t => <Tile key={t.id} trade={t} onClick={() => onClick(t)} />)}
      </div>
    </div>
  );
}

function Tile({ trade, onClick }: { trade: Trade; onClick: () => void }) {
  const statusClass =
    trade.status === "win" ? "tag-green" :
    trade.status === "loss" ? "tag-red" :
    trade.status === "breakeven" ? "tag-yellow" : "tag-blue";
  return (
    <div className="card" style={{ padding: 8, cursor: "pointer" }} onClick={onClick}>
      <div className="flex between center" style={{ gap: 4 }}>
        <span className="font-500" style={{ fontSize: 13 }}>{trade.pair}</span>
        <span className={`tag ${statusClass}`} style={{ fontSize: 10 }}>{trade.status.toUpperCase()}</span>
      </div>
      <div className="text-xs text-2" style={{ marginTop: 4 }}>
        {trade.direction} · {trade.timeframe}
        {trade.pnl != null && <span> · {trade.pnl >= 0 ? "+" : ""}${trade.pnl}</span>}
      </div>
    </div>
  );
}
