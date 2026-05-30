import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, Trade } from "../api";
import ChartEmbed from "./ChartEmbed";
import TrailedStopsTable from "./TrailedStopsTable";
import CloseTradePanel from "./CloseTradePanel";
import EditableField from "./EditableField";

export default function TradeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [trade, setTrade] = useState<Trade | null>(null);
  const [editing, setEditing] = useState(false);
  const [closing, setClosing] = useState(false);
  const [draft, setDraft] = useState<Partial<Trade>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.getTrade(Number(id))
      .then(t => { if (!cancelled) { setTrade(t); setDraft(t); } })
      .catch(() => { if (!cancelled) navigate("/"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id, navigate]);

  if (loading) return <div className="text-2 text-sm">Loading…</div>;
  if (!trade) return null;

  const startEdit = () => { setDraft(trade); setEditing(true); };
  const cancelEdit = () => { setDraft(trade); setEditing(false); };
  const save = async () => {
    setBusy(true);
    try {
      const updated = await api.updateTrade(trade.id, draft);
      setTrade(updated);
      setDraft(updated);
      setEditing(false);
    } finally { setBusy(false); }
  };
  const remove = async () => {
    if (!confirm("Delete this trade permanently?")) return;
    await api.deleteTrade(trade.id);
    navigate("/");
  };

  const F = (label: string, key: keyof Trade, type: "text" | "number" | "textarea" = "text") => (
    <EditableField
      label={label}
      value={(editing ? draft[key] : trade[key]) as any}
      type={type}
      editing={editing}
      onChange={v => setDraft(d => ({ ...d, [key]: type === "number" ? (v === "" ? null : parseFloat(v)) : v }))}
    />
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div className="flex between center wrap">
        <div className="flex gap-2 center wrap">
          <button className="btn btn-ghost btn-sm" onClick={() => navigate("/")}>← Back</button>
          <span className="font-500">{trade.pair}</span>
          <span className={`tag ${trade.direction === "LONG" ? "tag-green" : "tag-red"}`}>{trade.direction}</span>
          <span className="tag tag-blue">{trade.timeframe}</span>
          <span className="tag tag-blue">{trade.strategy}</span>
          <span className={`tag ${
            trade.status === "win" ? "tag-green" :
            trade.status === "loss" ? "tag-red" :
            trade.status === "breakeven" ? "tag-yellow" : "tag-blue"
          }`}>{trade.status.toUpperCase()}</span>
        </div>
        <div className="flex gap-2">
          {editing ? (
            <>
              <button className="btn btn-primary btn-sm" disabled={busy} onClick={save}>Save</button>
              <button className="btn btn-ghost btn-sm" disabled={busy} onClick={cancelEdit}>Cancel</button>
            </>
          ) : (
            <>
              <button className="btn btn-ghost btn-sm" onClick={startEdit}>Edit</button>
              {trade.status === "entered" && !closing && (
                <button className="btn btn-primary btn-sm" onClick={() => setClosing(true)}>Close trade</button>
              )}
              <button className="btn btn-ghost btn-sm" style={{ color: "var(--red)" }} onClick={remove}>Delete</button>
            </>
          )}
        </div>
      </div>

      {/* Chart */}
      <ChartEmbed snapshotUrl={trade.chart_url || ""} symbol={trade.pair} timeframe={trade.timeframe} />

      {/* Numbers strip */}
      <div className="card">
        <div className="flex gap-4 wrap">
          {F("Entry", "entry_price", "number")}
          {F("Exit", "exit_price", "number")}
          {F("Original SL", "stop_loss", "number")}
          {F("TP", "take_profit", "number")}
          {F("Size", "position_size", "number")}
          {F("Account", "account_size", "number")}
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span className="text-xs text-2">Risk $</span>
            <span className="text-sm">{trade.risk_dollars ?? "—"}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span className="text-xs text-2">Risk %</span>
            <span className="text-sm">{trade.risk_percent ?? "—"}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span className="text-xs text-2">R achieved</span>
            <span className="text-sm">{trade.rr_achieved ?? "—"}</span>
          </div>
          {trade.r_locked_at_penultimate_trail != null && (
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span className="text-xs text-2">R locked (-1th trail)</span>
              <span className="text-sm">{trade.r_locked_at_penultimate_trail}</span>
            </div>
          )}
          {F("P&L", "pnl", "number")}
        </div>
      </div>

      {/* Trailed stops */}
      <TrailedStopsTable trade={trade} onChange={setTrade} />

      {/* Close panel (only when status is entered AND user clicked Close) */}
      {closing && trade.status === "entered" && (
        <CloseTradePanel trade={trade} onClosed={t => { setTrade(t); setClosing(false); }} onCancel={() => setClosing(false)} />
      )}

      {/* Plan/process */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Plan / Process</h3>
        <div className="flex gap-4 wrap">
          {F("Setup score", "setup_score", "number")}
          {F("Verdict", "verdict")}
        </div>
        {F("Notes", "notes", "textarea")}
        <div style={{ marginTop: 8 }}>
          <div className="text-xs text-2">Confluences</div>
          <div className="chip-row">
            {(trade.confluences || []).map(c => <span key={c} className="chip selected">{c.replace(/_/g, " ")}</span>)}
          </div>
        </div>
      </div>

      {/* Outcome */}
      {(["win", "loss", "breakeven"] as const).includes(trade.status as any) && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Outcome</h3>
          {F("Lessons", "lessons", "textarea")}
          {F("Feelings at exit", "feelings_exit", "textarea")}
          <div style={{ marginTop: 8 }}>
            <div className="text-xs text-2">Mistake tags</div>
            <div className="chip-row">
              {(trade.mistake_tags || []).map(c => <span key={c} className="chip selected">{c.replace(/_/g, " ")}</span>)}
            </div>
          </div>
        </div>
      )}

      {trade.updated_at && trade.updated_at !== trade.created_at && (
        <div className="text-xs text-2">Last edited: {new Date(trade.updated_at).toLocaleString()}</div>
      )}
    </div>
  );
}
