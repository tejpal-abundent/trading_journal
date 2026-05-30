import { useState } from "react";
import { api, Trade } from "../api";

interface Props {
  trade: Trade;
  onClosed: (t: Trade) => void;
  onCancel: () => void;
}

type Status = "win" | "loss" | "breakeven";

export default function CloseTradePanel({ trade, onClosed, onCancel }: Props) {
  const [status, setStatus] = useState<Status>("win");
  const [exitPrice, setExitPrice] = useState("");
  const [pnl, setPnl] = useState("");
  const [mistakeTags, setMistakeTags] = useState("");
  const [emotionsExit, setEmotionsExit] = useState("");
  const [feelingsExit, setFeelingsExit] = useState("");
  const [lessons, setLessons] = useState("");
  const [rulesFollowed, setRulesFollowed] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const exit = parseFloat(exitPrice);
    if (Number.isNaN(exit)) { alert("exit_price required"); return; }
    setBusy(true);
    try {
      const updated = await api.closeTrade(trade.id, {
        status,
        exit_price: exit,
        pnl: pnl === "" ? null : parseFloat(pnl),
        rules_followed: rulesFollowed,
        mistake_tags: mistakeTags.split(",").map(s => s.trim()).filter(Boolean),
        emotions_exit: emotionsExit.split(",").map(s => s.trim()).filter(Boolean),
        feelings_exit: feelingsExit,
        lessons,
      });
      onClosed(updated);
    } finally { setBusy(false); }
  };

  return (
    <div className="card" style={{ borderLeft: "3px solid var(--blue)" }}>
      <h3 style={{ marginTop: 0 }}>Close trade</h3>
      <div className="flex gap-2 wrap" style={{ marginBottom: 8 }}>
        {(["win", "loss", "breakeven"] as Status[]).map(s => (
          <button key={s} className={`btn btn-sm ${status === s ? "btn-primary" : "btn-ghost"}`} onClick={() => setStatus(s)}>{s}</button>
        ))}
      </div>
      <div className="flex gap-2 wrap" style={{ marginBottom: 8 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span className="text-xs text-2">Exit price *</span>
          <input className="input" type="number" value={exitPrice} onChange={e => setExitPrice(e.target.value)} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span className="text-xs text-2">P&L (optional override)</span>
          <input className="input" type="number" value={pnl} onChange={e => setPnl(e.target.value)} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span className="text-xs text-2">Plan followed?</span>
          <div className="flex gap-1">
            {[true, false, null].map((v, i) => (
              <button key={i} className={`btn btn-sm ${rulesFollowed === v ? "btn-primary" : "btn-ghost"}`} onClick={() => setRulesFollowed(v)}>
                {v === true ? "Yes" : v === false ? "No" : "—"}
              </button>
            ))}
          </div>
        </label>
      </div>
      <label style={{ display: "block", marginBottom: 8 }}>
        <span className="text-xs text-2">Mistake tags (comma-separated)</span>
        <input className="input" type="text" value={mistakeTags} onChange={e => setMistakeTags(e.target.value)} style={{ width: "100%" }} />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        <span className="text-xs text-2">Emotions at exit (comma-separated)</span>
        <input className="input" type="text" value={emotionsExit} onChange={e => setEmotionsExit(e.target.value)} style={{ width: "100%" }} />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        <span className="text-xs text-2">Feelings at exit</span>
        <textarea className="input" rows={2} value={feelingsExit} onChange={e => setFeelingsExit(e.target.value)} style={{ width: "100%" }} />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        <span className="text-xs text-2">Lessons</span>
        <textarea className="input" rows={3} value={lessons} onChange={e => setLessons(e.target.value)} style={{ width: "100%" }} />
      </label>
      <div className="flex gap-2" style={{ marginTop: 8 }}>
        <button className="btn btn-primary" disabled={busy} onClick={submit}>Close trade</button>
        <button className="btn btn-ghost" disabled={busy} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}
