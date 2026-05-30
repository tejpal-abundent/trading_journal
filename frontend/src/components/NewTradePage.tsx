import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";

export default function NewTradePage() {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const isRetro = search.get("mode") === "retro";

  const [pair, setPair] = useState("");
  const [direction, setDirection] = useState<"LONG" | "SHORT">("LONG");
  const [timeframe, setTimeframe] = useState("15m");
  const [strategy, setStrategy] = useState("Zone Failure");
  const [setupScore, setSetupScore] = useState("80");
  const [verdict, setVerdict] = useState("A");
  const [entryPrice, setEntryPrice] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [positionSize, setPositionSize] = useState("");
  const [accountSize, setAccountSize] = useState("");
  const [notes, setNotes] = useState("");
  const [chartUrl, setChartUrl] = useState("");
  const [busy, setBusy] = useState(false);

  // Retro extras
  const [exitPrice, setExitPrice] = useState("");
  const [status, setStatus] = useState<"win" | "loss" | "breakeven">("win");
  const [pnl, setPnl] = useState("");

  const submit = async () => {
    setBusy(true);
    try {
      if (isRetro) {
        const t = await api.createRetroactiveTrade({
          pair, direction, timeframe, strategy,
          setup_score: parseInt(setupScore) || 0, verdict,
          criteria_checked: [], confluences: [], notes,
          entry_price: parseFloat(entryPrice), stop_loss: parseFloat(stopLoss),
          take_profit: takeProfit === "" ? null : parseFloat(takeProfit),
          position_size: positionSize === "" ? null : parseFloat(positionSize),
          account_size: accountSize === "" ? null : parseFloat(accountSize),
          status, exit_price: parseFloat(exitPrice),
          pnl: pnl === "" ? null : parseFloat(pnl),
          chart_url: chartUrl,
        });
        navigate(`/trade/${t.id}`);
      } else {
        const t = await api.createTrade({
          pair, direction, timeframe, strategy,
          setup_score: parseInt(setupScore) || 0, verdict,
          criteria_checked: [], confluences: [], notes,
          entry_price: parseFloat(entryPrice), stop_loss: parseFloat(stopLoss),
          take_profit: takeProfit === "" ? null : parseFloat(takeProfit),
          position_size: parseFloat(positionSize),
          account_size: parseFloat(accountSize),
          chart_url: chartUrl,
        });
        navigate(`/trade/${t.id}`);
      }
    } finally { setBusy(false); }
  };

  return (
    <div className="card" style={{ maxWidth: 700 }}>
      <h2 style={{ marginTop: 0 }}>{isRetro ? "Log closed trade" : "New trade"}</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <Field label="Pair" value={pair} onChange={setPair} />
        <Field label="Direction" value={direction} onChange={v => setDirection(v as any)} />
        <Field label="Timeframe" value={timeframe} onChange={setTimeframe} />
        <Field label="Strategy" value={strategy} onChange={setStrategy} />
        <Field label="Setup score" value={setupScore} onChange={setSetupScore} type="number" />
        <Field label="Verdict" value={verdict} onChange={setVerdict} />
        <Field label="Entry price" value={entryPrice} onChange={setEntryPrice} type="number" />
        <Field label="Stop loss" value={stopLoss} onChange={setStopLoss} type="number" />
        <Field label="Take profit (opt)" value={takeProfit} onChange={setTakeProfit} type="number" />
        <Field label="Position size" value={positionSize} onChange={setPositionSize} type="number" />
        <Field label="Account size" value={accountSize} onChange={setAccountSize} type="number" />
        <Field label="Chart URL (opt)" value={chartUrl} onChange={setChartUrl} />
      </div>
      {isRetro && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginTop: 8 }}>
          <Field label="Status" value={status} onChange={v => setStatus(v as any)} />
          <Field label="Exit price" value={exitPrice} onChange={setExitPrice} type="number" />
          <Field label="P&L" value={pnl} onChange={setPnl} type="number" />
        </div>
      )}
      <label style={{ display: "block", marginTop: 8 }}>
        <span className="text-xs text-2">Notes</span>
        <textarea className="input" rows={3} value={notes} onChange={e => setNotes(e.target.value)} style={{ width: "100%" }} />
      </label>
      <div className="flex gap-2" style={{ marginTop: 12 }}>
        <button className="btn btn-primary" disabled={busy || !pair} onClick={submit}>
          {isRetro ? "Log trade" : "Create trade"}
        </button>
        <button className="btn btn-ghost" onClick={() => navigate("/")}>Cancel</button>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span className="text-xs text-2">{label}</span>
      <input className="input" type={type} value={value} onChange={e => onChange(e.target.value)} />
    </label>
  );
}
