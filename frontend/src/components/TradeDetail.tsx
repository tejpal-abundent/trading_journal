import { useState } from "react";
import { api, Trade } from "../api";
import EnterTradeForm from "./EnterTradeForm";
import SkipTradeForm from "./SkipTradeForm";
import CloseTradeForm from "./CloseTradeForm";
import { labelize } from "../constants/tags";

interface Props {
  trade: Trade;
  onClose: () => void;
  onChanged: (t: Trade | null) => void;
}

type Section = "plan" | "execution" | "result";
type Mode = "view" | "enter" | "skip" | "close";

export default function TradeDetail({ trade, onClose, onChanged }: Props) {
  const [open, setOpen] = useState<Section>("plan");
  const [mode, setMode] = useState<Mode>("view");

  const remove = async () => {
    if (!confirm("Delete this trade?")) return;
    await api.deleteTrade(trade.id);
    onChanged(null);
    onClose();
  };

  const Plan = (
    <div>
      <div className="flex gap-2 wrap mb-2">
        <span className="font-500">{trade.pair}</span>
        <span className={`tag ${trade.direction === "LONG" ? "tag-green" : "tag-red"}`}>{trade.direction}</span>
        <span className="tag tag-blue">{trade.timeframe}</span>
        <span className="tag tag-blue">{trade.strategy}</span>
        <span className="font-500">{trade.setup_score}/100</span>
      </div>
      <div className="text-xs text-2">{trade.verdict}</div>
      {(trade.planned_entry != null || trade.planned_stop != null || trade.planned_target != null) && (
        <div className="text-sm mt-2">
          Plan: entry {trade.planned_entry ?? "—"} · stop {trade.planned_stop ?? "—"} · target {trade.planned_target ?? "—"}
          {trade.planned_rr != null && ` · R:R ${trade.planned_rr}`}
        </div>
      )}
      {trade.notes && <div className="text-sm text-2 mt-2" style={{ fontStyle: "italic" }}>{trade.notes}</div>}
    </div>
  );

  const Execution = trade.status === "planned" ? (
    <div className="flex gap-2">
      <button className="btn btn-sm btn-primary" onClick={() => setMode("enter")}>Mark as Entered</button>
      <button className="btn btn-sm btn-ghost" onClick={() => setMode("skip")}>Mark as Skipped</button>
    </div>
  ) : trade.status === "skipped" ? (
    <div className="text-sm">
      <b>Skipped</b> — {trade.skip_reason}
      {trade.emotions_entry.length > 0 && (
        <div className="text-xs text-2 mt-1">Felt: {trade.emotions_entry.map(labelize).join(", ")}</div>
      )}
    </div>
  ) : (
    <div className="text-sm">
      Entry {trade.entry_price ?? "—"} · Stop {trade.stop_loss ?? "—"} · TP {trade.take_profit ?? "—"}<br/>
      Position {trade.position_size ?? "—"} · Account ${trade.account_size ?? "—"}<br/>
      <b>Risk:</b> ${trade.risk_dollars ?? "—"} ({trade.risk_percent ?? "—"}% of account)
      {trade.entry_timing && <span> · {labelize(trade.entry_timing)}</span>}
      {trade.emotions_entry.length > 0 && (
        <div className="text-xs text-2 mt-1">Felt at entry: {trade.emotions_entry.map(labelize).join(", ")}</div>
      )}
      {trade.feelings_entry && (
        <div className="text-xs text-2 mt-1" style={{ fontStyle: "italic" }}>{trade.feelings_entry}</div>
      )}
    </div>
  );

  const Result = trade.status === "entered" ? (
    <button className="btn btn-sm btn-primary" onClick={() => setMode("close")}>Close Trade</button>
  ) : ["win", "loss", "breakeven"].includes(trade.status) ? (
    <div className="text-sm">
      <b style={{ color: trade.status === "win" ? "var(--green)" : trade.status === "loss" ? "var(--red)" : "var(--yellow)" }}>
        {trade.status.toUpperCase()}
      </b>
      {" "}· Exit {trade.exit_price ?? "—"}
      {trade.pnl != null && <> · P/L ${trade.pnl}</>}
      {trade.rr_achieved != null && <> · R:R {trade.rr_achieved}</>}
      <div className="mt-1">
        Plan followed: <b>{trade.rules_followed === true ? "Yes" : trade.rules_followed === false ? "No" : "—"}</b>
      </div>
      {trade.mistake_tags.length > 0 && (
        <div className="mt-1 text-xs text-2">Mistakes: {trade.mistake_tags.map(labelize).join(", ")}</div>
      )}
      {trade.emotions_exit.length > 0 && (
        <div className="mt-1 text-xs text-2">Felt at exit: {trade.emotions_exit.map(labelize).join(", ")}</div>
      )}
      {trade.lessons && (
        <div className="mt-2 text-sm" style={{ fontStyle: "italic" }}>Lessons: {trade.lessons}</div>
      )}
      {trade.chart_url && (
        <div className="mt-2"><a href={trade.chart_url} target="_blank" rel="noreferrer">📈 Chart</a></div>
      )}
    </div>
  ) : (
    <div className="text-2 text-xs">Mark as Entered first.</div>
  );

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={e => e.stopPropagation()}>
        <div className="flex between center mb-3">
          <h2 style={{ fontSize: 18 }}>{trade.pair} {trade.direction}</h2>
          <button className="btn btn-sm btn-ghost" onClick={onClose}>×</button>
        </div>

        {mode === "view" && (
          <>
            <Section title="Plan" body={Plan} open={open === "plan"} onToggle={() => setOpen("plan")} />
            <Section title="Execution" body={Execution} open={open === "execution"} onToggle={() => setOpen("execution")} />
            <Section title="Result" body={Result} open={open === "result"} onToggle={() => setOpen("result")} />

            <div className="flex gap-2 mt-3" style={{ justifyContent: "flex-end" }}>
              <button className="btn btn-sm btn-ghost" style={{ color: "var(--red)" }} onClick={remove}>Delete trade</button>
            </div>
          </>
        )}
        {mode === "enter" && (
          <EnterTradeForm trade={trade}
            onSaved={t => { setMode("view"); onChanged(t); }}
            onCancel={() => setMode("view")} />
        )}
        {mode === "skip" && (
          <SkipTradeForm trade={trade}
            onSaved={t => { setMode("view"); onChanged(t); }}
            onCancel={() => setMode("view")} />
        )}
        {mode === "close" && (
          <CloseTradeForm trade={trade}
            onSaved={t => { setMode("view"); onChanged(t); }}
            onCancel={() => setMode("view")} />
        )}
      </div>
    </div>
  );
}

function Section({ title, body, open, onToggle }: {
  title: string; body: React.ReactNode; open: boolean; onToggle: () => void;
}) {
  return (
    <div className="accordion">
      <div className="accordion-header" onClick={onToggle}>
        <b>{title}</b>
        <span>{open ? "▾" : "▸"}</span>
      </div>
      {open && <div className="accordion-body">{body}</div>}
    </div>
  );
}
