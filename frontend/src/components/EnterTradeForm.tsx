import { useEffect, useState } from "react";
import { api, Trade, EntryTiming } from "../api";
import { computeRisk } from "../lib/risk";
import { ENTRY_TIMING, EMOTION_TAGS, labelize } from "../constants/tags";
import TagChips from "./TagChips";
import AccountBalanceModal from "./AccountBalanceModal";

interface Props {
  trade: Trade;
  onSaved: (t: Trade) => void;
  onCancel: () => void;
}

export default function EnterTradeForm({ trade, onSaved, onCancel }: Props) {
  const [entry, setEntry] = useState(trade.planned_entry?.toString() || "");
  const [stop, setStop]  = useState(trade.planned_stop?.toString()  || "");
  const [target, setTarget] = useState(trade.planned_target?.toString() || "");
  const [posSize, setPosSize] = useState("1");
  const [acctSize, setAcctSize] = useState<string>("");
  const [timing, setTiming] = useState<EntryTiming | "">("on_time");
  const [emotions, setEmotions] = useState<string[]>([]);
  const [feelings, setFeelings] = useState("");
  const [showBalance, setShowBalance] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.latestSnapshot().then(s => {
      if (s.balance != null) setAcctSize(String(s.balance));
    });
  }, []);

  const e = parseFloat(entry); const s = parseFloat(stop);
  const ps = parseFloat(posSize); const ac = parseFloat(acctSize);
  const risk = computeRisk(
    isFinite(e) ? e : null,
    isFinite(s) ? s : null,
    isFinite(ps) ? ps : null,
    isFinite(ac) ? ac : null,
  );

  const save = async () => {
    if (!entry || !stop || !posSize || !acctSize || saving) return;
    setSaving(true);
    try {
      const t = await api.enterTrade(trade.id, {
        entry_price: parseFloat(entry),
        stop_loss: parseFloat(stop),
        take_profit: target ? parseFloat(target) : null,
        position_size: parseFloat(posSize),
        account_size: parseFloat(acctSize),
        entry_timing: (timing || null),
        emotions_entry: emotions,
        feelings_entry: feelings,
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
      <div className="flex gap-2">
        <div className="grow">
          <label className="text-xs text-2">Actual entry</label>
          <input type="number" step="any" value={entry} onChange={ev => setEntry(ev.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">Actual stop</label>
          <input type="number" step="any" value={stop} onChange={ev => setStop(ev.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">Take profit</label>
          <input type="number" step="any" value={target} onChange={ev => setTarget(ev.target.value)} />
        </div>
      </div>

      <div className="flex gap-2 center">
        <div className="grow">
          <label className="text-xs text-2">Position size</label>
          <input type="number" step="any" value={posSize} onChange={ev => setPosSize(ev.target.value)} />
        </div>
        <div className="grow">
          <label className="text-xs text-2">Account size ($)</label>
          <input type="number" step="any" value={acctSize} onChange={ev => setAcctSize(ev.target.value)} />
        </div>
        <button className="btn btn-sm btn-ghost" style={{ marginTop: 16 }}
          onClick={() => setShowBalance(true)}>Update</button>
      </div>

      {risk.risk_dollars != null && (
        <div className={`risk-display ${risk.risk_percent != null && risk.risk_percent > 2 ? "warn" : ""}`}>
          Risk: ${risk.risk_dollars}
          {risk.risk_percent != null && ` (${risk.risk_percent}% of account)`}
        </div>
      )}

      <div>
        <label className="text-xs text-2">Entry timing</label>
        <div className="flex gap-1 mt-1">
          {ENTRY_TIMING.map(t => (
            <button key={t} className={`btn btn-sm ${timing === t ? "btn-primary" : "btn-ghost"}`}
              onClick={() => setTiming(t)}>{labelize(t)}</button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs text-2">Feelings at entry</label>
        <TagChips options={EMOTION_TAGS} selected={emotions} onChange={setEmotions} />
      </div>

      <textarea placeholder="What was going through my head"
        value={feelings} onChange={ev => setFeelings(ev.target.value)} rows={2} />

      <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-sm btn-ghost" onClick={onCancel}>Cancel</button>
        <button className="btn btn-sm btn-primary" onClick={save} disabled={saving}>
          {saving ? "Saving..." : "Mark as Entered"}
        </button>
      </div>

      <AccountBalanceModal
        open={showBalance}
        onClose={() => setShowBalance(false)}
        current={isFinite(ac) ? ac : null}
        onSaved={(b) => setAcctSize(String(b))}
      />
    </div>
  );
}
