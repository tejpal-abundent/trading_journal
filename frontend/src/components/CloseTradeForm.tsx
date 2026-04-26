import { useState } from "react";
import { api, Trade, PartialExit, CloseStatus } from "../api";
import { MISTAKE_TAGS, EMOTION_TAGS } from "../constants/tags";
import TagChips from "./TagChips";
import PartialExits from "./PartialExits";

interface Props {
  trade: Trade;
  onSaved: (t: Trade) => void;
  onCancel: () => void;
}

export default function CloseTradeForm({ trade, onSaved, onCancel }: Props) {
  const [status, setStatus] = useState<CloseStatus>("win");
  const [exitPrice, setExitPrice] = useState(trade.exit_price?.toString() || "");
  const [pnl, setPnl] = useState(trade.pnl?.toString() || "");
  const [pnlPct, setPnlPct] = useState(trade.pnl_percent?.toString() || "");
  const [rr, setRr] = useState(trade.rr_achieved?.toString() || "");
  const [rulesFollowed, setRulesFollowed] = useState<boolean | null>(true);
  const [mistakes, setMistakes] = useState<string[]>(trade.mistake_tags || []);
  const [emotions, setEmotions] = useState<string[]>(trade.emotions_exit || []);
  const [feelings, setFeelings] = useState(trade.feelings_exit || "");
  const [lessons, setLessons] = useState(trade.lessons || "");
  const [chartUrl, setChartUrl] = useState(trade.chart_url || "");
  const [partials, setPartials] = useState<PartialExit[]>(trade.partial_exits || []);
  const [mfeR, setMfeR] = useState(trade.mfe_r != null ? String(trade.mfe_r) : "");
  const [maeR, setMaeR] = useState(trade.mae_r != null ? String(trade.mae_r) : "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!exitPrice || saving) return;
    setSaving(true);
    try {
      const t = await api.closeTrade(trade.id, {
        status,
        exit_price: parseFloat(exitPrice),
        pnl: pnl ? parseFloat(pnl) : null,
        pnl_percent: pnlPct ? parseFloat(pnlPct) : null,
        rr_achieved: rr ? parseFloat(rr) : null,
        rules_followed: rulesFollowed,
        mistake_tags: mistakes,
        emotions_exit: emotions,
        feelings_exit: feelings,
        lessons,
        chart_url: chartUrl,
        partial_exits: partials,
        mfe_r: mfeR ? parseFloat(mfeR) : null,
        mae_r: maeR ? parseFloat(maeR) : null,
      });
      onSaved(t);
    } catch (err) {
      alert("Failed: " + (err instanceof Error ? err.message : "Unknown"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex col gap-2">
      <div className="flex gap-1">
        {(["win", "loss", "breakeven"] as CloseStatus[]).map(s => (
          <button key={s} className={`btn btn-sm ${status === s ? "btn-primary" : "btn-ghost"}`}
            style={{ background: status === s ? (s === "win" ? "var(--green)" : s === "loss" ? "var(--red)" : "var(--yellow)") : undefined,
                     color: status === s ? "#fff" : undefined }}
            onClick={() => setStatus(s)}>{s.toUpperCase()}</button>
        ))}
      </div>

      <div className="flex gap-2">
        <div className="grow">
          <label className="text-xs text-2">Exit price</label>
          <input type="number" step="any" value={exitPrice} onChange={e => setExitPrice(e.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">P/L ($)</label>
          <input type="number" step="any" value={pnl} onChange={e => setPnl(e.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">P/L %</label>
          <input type="number" step="any" value={pnlPct} onChange={e => setPnlPct(e.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">R:R</label>
          <input type="number" step="any" value={rr} onChange={e => setRr(e.target.value)} />
        </div>
      </div>

      <div className="card" style={{ background: "var(--bg2)", padding: "10px 12px", marginBottom: 0 }}>
        <div className="text-xs text-2 mb-1">
          <b>MFE / MAE (in R-multiples)</b> — how far the trade went in your favor / against you, regardless of where you exited. Powers entry & target optimization.
        </div>
        <div className="flex gap-2">
          <div className="grow">
            <label className="text-xs text-2">MFE (max favorable, in R)</label>
            <input type="number" step="any" placeholder="e.g. 1.8"
              value={mfeR} onChange={e => setMfeR(e.target.value)} />
          </div>
          <div className="grow">
            <label className="text-xs text-2">MAE (max adverse, in R)</label>
            <input type="number" step="any" placeholder="e.g. 0.4"
              value={maeR} onChange={e => setMaeR(e.target.value)} />
          </div>
        </div>
      </div>

      <div>
        <label className="text-xs text-2">Partial exits</label>
        <PartialExits value={partials} onChange={setPartials} />
      </div>

      <div>
        <label className="text-xs text-2">Did you follow your plan?</label>
        <div className="flex gap-1 mt-1">
          <button className={`btn btn-sm ${rulesFollowed === true ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setRulesFollowed(true)}>Yes</button>
          <button className={`btn btn-sm ${rulesFollowed === false ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setRulesFollowed(false)}>No</button>
        </div>
      </div>

      <div>
        <label className="text-xs text-2">Mistakes</label>
        <TagChips options={MISTAKE_TAGS} selected={mistakes} onChange={setMistakes} variant="mistake" />
      </div>

      <div>
        <label className="text-xs text-2">Feelings at exit</label>
        <TagChips options={EMOTION_TAGS} selected={emotions} onChange={setEmotions} />
      </div>

      <textarea placeholder="What was going through my head" rows={2}
        value={feelings} onChange={e => setFeelings(e.target.value)} />

      <textarea placeholder="Lessons learned" rows={3}
        value={lessons} onChange={e => setLessons(e.target.value)} />

      <input placeholder="TradingView chart URL"
        value={chartUrl} onChange={e => setChartUrl(e.target.value)} />

      <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-sm btn-ghost" onClick={onCancel}>Cancel</button>
        <button className="btn btn-sm btn-primary" onClick={save} disabled={saving || !exitPrice}>
          {saving ? "Saving..." : "Close Trade"}
        </button>
      </div>
    </div>
  );
}
