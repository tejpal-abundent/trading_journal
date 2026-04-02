import { useState } from "react";
import { api } from "../api";

const criteria = [
  { id: "trend", label: "Trade is in direction of the overall trend", points: 20, category: "Core", desc: "Downtrend = only short setups, Uptrend = only long setups" },
  { id: "zone", label: "Pattern formed at a KEY zone (S/R, trendline, EMA)", points: 15, category: "Core", desc: "Not in mid-range / no man's land" },
  { id: "signal", label: "Signal candle present (Hammer / Hanging Man)", points: 15, category: "Core", desc: "The trap candle that baits traders the wrong way" },
  { id: "failure", label: "Next candle is solid body AGAINST the signal candle", points: 20, category: "Core", desc: "Solid red after hammer = SHORT | Solid green after hanging man = LONG" },
  { id: "body", label: "Failure candle has large real body (>60% of total range)", points: 5, category: "Quality", desc: "Shows conviction, not a weak doji" },
  { id: "wick", label: "Signal candle wick is 2x+ the body", points: 5, category: "Quality", desc: "Shows deep rejection that trapped more traders" },
  { id: "stop", label: "Stop placed beyond signal candle wick (clear invalidation)", points: 5, category: "Risk", desc: "If price goes past the trap wick, thesis is wrong" },
  { id: "rr", label: "R:R is at least 1:2 to next zone", points: 5, category: "Risk", desc: "Target must be at least 2x your stop distance" },
  { id: "htf", label: "Higher timeframe structure agrees", points: 5, category: "Quality", desc: "4H setup confirmed by Daily trend direction" },
  { id: "macro", label: "No major news in next 4 hours", points: 3, category: "Timing", desc: "Avoid FOMC, NFP, BOJ etc within 4 hours" },
  { id: "volume", label: "Failure candle shows increased volume/momentum", points: 2, category: "Quality", desc: "Trapped traders exiting = visible momentum" },
];

const CORE_IDS = ["trend", "zone", "signal", "failure"];

export default function TradeChecklist() {
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [pair, setPair] = useState("");
  const [tf, setTf] = useState("4H");
  const [dir, setDir] = useState("SHORT");
  const [notes, setNotes] = useState("");
  const [showDesc, setShowDesc] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const toggle = (id: string) => setChecked(p => ({ ...p, [id]: !p[id] }));

  const score = criteria.reduce((s, c) => s + (checked[c.id] ? c.points : 0), 0);
  const coresMet = CORE_IDS.every(id => checked[id]);

  const getVerdict = () => {
    if (score >= 85 && coresMet) return { text: "A+ SETUP -- Full size, this is your edge", color: "var(--green)" };
    if (score >= 70 && coresMet) return { text: "B SETUP -- Reduced size, solid enough", color: "var(--yellow)" };
    if (score >= 55 && coresMet) return { text: "C SETUP -- Marginal, consider skipping", color: "#D85A30" };
    if (!coresMet) return { text: "MISSING CORE -- Do NOT trade", color: "var(--red)" };
    return { text: "SKIP -- Not enough confluence", color: "var(--red)" };
  };

  const verdict = getVerdict();

  const logTrade = async () => {
    if (!pair || saving) return;
    setSaving(true);
    try {
      await api.createTrade({
        pair,
        direction: dir,
        timeframe: tf,
        setup_score: score,
        verdict: verdict.text,
        criteria_checked: Object.keys(checked).filter(k => checked[k]),
        notes,
      });
      setSaved(true);
      setChecked({});
      setPair("");
      setNotes("");
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      alert("Failed to save trade");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <p className="text-sm text-2 mb-3" style={{ lineHeight: 1.6 }}>
        Zone failure strategy: Hammer &rarr; solid red = SHORT | Hanging man &rarr; solid green = LONG
      </p>

      <div className="flex gap-2 wrap mb-3">
        <input
          placeholder="Pair (e.g. XAG/USD)"
          value={pair}
          onChange={e => setPair(e.target.value.toUpperCase())}
          style={{ flex: 1, minWidth: 120 }}
        />
        {["1H", "2H", "4H"].map(t => (
          <button key={t} onClick={() => setTf(t)}
            className={`btn btn-sm ${tf === t ? "btn-primary" : "btn-ghost"}`}>
            {t}
          </button>
        ))}
        {["SHORT", "LONG"].map(d => (
          <button key={d} onClick={() => setDir(d)}
            className="btn btn-sm"
            style={{
              background: dir === d ? (d === "LONG" ? "var(--green-bg)" : "var(--red-bg)") : "transparent",
              color: d === "LONG" ? "var(--green)" : "var(--red)",
              border: `1.5px solid ${dir === d ? (d === "LONG" ? "var(--green)" : "var(--red)") : "var(--border)"}`,
              fontWeight: dir === d ? 600 : 400,
            }}>
            {d}
          </button>
        ))}
      </div>

      <div className="flex col gap-2">
        {criteria.map(c => {
          const isCore = CORE_IDS.includes(c.id);
          return (
            <div key={c.id}>
              <div onClick={() => toggle(c.id)} className="card" style={{
                cursor: "pointer",
                borderColor: checked[c.id] ? "var(--blue)" : isCore ? "var(--border2)" : "var(--border)",
                background: checked[c.id] ? "var(--blue-bg)" : "var(--bg2)",
                padding: "10px 14px", marginBottom: 0,
              }}>
                <div className="flex center gap-2">
                  <div style={{
                    width: 22, height: 22, borderRadius: 6, flexShrink: 0,
                    border: `2px solid ${checked[c.id] ? "var(--blue)" : "var(--border2)"}`,
                    background: checked[c.id] ? "var(--blue)" : "transparent",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "#fff", fontSize: 14, fontWeight: 700,
                  }}>
                    {checked[c.id] ? "\u2713" : ""}
                  </div>
                  <div className="grow">
                    <span className="text-sm">{c.label}</span>
                    {isCore && <span className="tag tag-red" style={{ marginLeft: 6 }}>CORE</span>}
                  </div>
                  <span className="text-xs text-2 font-500" style={{ flexShrink: 0 }}>+{c.points}</span>
                  <span onClick={e => { e.stopPropagation(); setShowDesc(showDesc === c.id ? null : c.id); }}
                    style={{
                      width: 20, height: 20, borderRadius: "50%", border: "1px solid var(--border)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 12, color: "var(--text2)", cursor: "pointer", flexShrink: 0,
                    }}>?</span>
                </div>
              </div>
              {showDesc === c.id && (
                <div className="text-xs text-2" style={{ padding: "6px 14px 6px 48px" }}>{c.desc}</div>
              )}
            </div>
          );
        })}
      </div>

      <div className="card mt-3" style={{ textAlign: "center", borderColor: verdict.color, borderWidth: 2 }}>
        <div style={{ fontSize: 40, fontWeight: 500, color: verdict.color }}>{score}/100</div>
        <div style={{ fontSize: 15, fontWeight: 500, color: verdict.color, marginTop: 4 }}>{verdict.text}</div>
        {pair && <div className="text-sm text-2 mt-2">{pair} | {dir} | {tf}</div>}
      </div>

      <textarea
        placeholder="Pre-trade notes (optional)"
        value={notes}
        onChange={e => setNotes(e.target.value)}
        rows={2}
        className="mt-3"
        style={{ resize: "vertical" }}
      />

      <button onClick={logTrade} disabled={!pair || saving}
        className="btn btn-primary mt-3"
        style={{ width: "100%" }}>
        {saved ? "Saved!" : saving ? "Saving..." : pair ? `Log ${pair} ${dir} & Save` : "Enter pair to log"}
      </button>
    </div>
  );
}
