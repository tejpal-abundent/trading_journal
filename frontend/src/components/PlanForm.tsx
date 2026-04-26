import { useEffect, useState } from "react";
import { api, Strategy } from "../api";
import StrategyManager from "./StrategyManager";
import ConfluenceInput from "./ConfluenceInput";

interface FormState {
  pair: string; tf: string; dir: "LONG" | "SHORT";
  notes: string;
  planned_entry: string; planned_stop: string; planned_target: string;
}

const initialForm: FormState = {
  pair: "", tf: "4H", dir: "SHORT",
  notes: "",
  planned_entry: "", planned_stop: "", planned_target: "",
};

export default function PlanForm() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategyId, setStrategyId] = useState<number | null>(null);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [form, setForm] = useState<FormState>(initialForm);
  const [confluences, setConfluences] = useState<string[]>([]);
  const [confluenceSuggestions, setConfluenceSuggestions] = useState<string[]>([]);
  const [showDesc, setShowDesc] = useState<string | null>(null);
  const [showStrategies, setShowStrategies] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const loadStrategies = () => {
    api.listStrategies().then(s => {
      setStrategies(s);
      setStrategyId(prev => prev ?? (s[0]?.id ?? null));
    });
  };

  useEffect(() => { loadStrategies(); }, []);

  useEffect(() => {
    api.listTrades().then(trades => {
      const counts = new Map<string, number>();
      trades.forEach(t => (t.confluences || []).forEach(c => counts.set(c, (counts.get(c) || 0) + 1)));
      const sorted = Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).map(([c]) => c);
      setConfluenceSuggestions(sorted);
    }).catch(() => {});
  }, []);

  const strategy = strategies.find(s => s.id === strategyId);
  const cores = strategy?.is_core_required || [];
  const hasCriteria = !!strategy && strategy.criteria.length > 0;

  const toggle = (id: string) => setChecked(p => ({ ...p, [id]: !p[id] }));

  const score = strategy
    ? strategy.criteria.reduce((s, c) => s + (checked[c.id] ? c.points : 0), 0)
    : 0;
  const coresMet = cores.every(id => checked[id]);

  const verdict = (() => {
    if (!strategy) return { text: "Select a strategy", color: "var(--text2)" };
    if (!hasCriteria) return { text: "Plan ready — qualify via confluences", color: "var(--text2)" };
    if (score >= 85 && coresMet) return { text: "A+ SETUP -- Full size, this is your edge", color: "var(--green)" };
    if (score >= 70 && coresMet) return { text: "B SETUP -- Reduced size, solid enough",      color: "var(--yellow)" };
    if (score >= 55 && coresMet) return { text: "C SETUP -- Marginal, consider skipping",     color: "#D85A30" };
    if (!coresMet)               return { text: "MISSING CORE -- Do NOT trade",                color: "var(--red)" };
    return { text: "SKIP -- Not enough confluence", color: "var(--red)" };
  })();

  const computedRR = (() => {
    const e = parseFloat(form.planned_entry);
    const s = parseFloat(form.planned_stop);
    const t = parseFloat(form.planned_target);
    if (!isFinite(e) || !isFinite(s) || !isFinite(t) || e === s) return null;
    return Math.round((Math.abs(t - e) / Math.abs(e - s)) * 100) / 100;
  })();

  const reset = () => { setChecked({}); setForm(initialForm); setConfluences([]); };

  const save = async () => {
    if (!form.pair || !strategy || saving) return;
    setSaving(true);
    try {
      const data: Parameters<typeof api.createPlan>[0] = {
        pair: form.pair, direction: form.dir, timeframe: form.tf,
        strategy: strategy.name,
        setup_score: score,
        verdict: verdict.text,
        criteria_checked: Object.keys(checked).filter(k => checked[k]),
        notes: form.notes,
      };
      if (form.planned_entry)  data.planned_entry  = parseFloat(form.planned_entry);
      if (form.planned_stop)   data.planned_stop   = parseFloat(form.planned_stop);
      if (form.planned_target) data.planned_target = parseFloat(form.planned_target);
      if (computedRR != null)  data.planned_rr     = computedRR;
      if (confluences.length)  data.confluences    = confluences;
      await api.createPlan(data);
      setConfluenceSuggestions(prev => Array.from(new Set([...confluences, ...prev])));
      setSaved(true);
      reset();
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      alert("Failed to save plan: " + (e instanceof Error ? e.message : "Unknown error"));
    } finally {
      setSaving(false);
    }
  };

  if (!strategy) {
    return <p className="text-2 text-sm">Loading strategies...</p>;
  }

  return (
    <div>
      <div className="flex gap-2 center mb-3">
        <label className="text-sm">Strategy:</label>
        <select value={strategyId ?? ""} onChange={e => setStrategyId(Number(e.target.value))}>
          {strategies.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <button className="btn btn-sm btn-ghost" onClick={() => setShowStrategies(true)}>
          Edit / new strategy
        </button>
      </div>

      <div className="flex gap-2 wrap mb-3">
        <input
          placeholder="Pair (e.g. XAG/USD)"
          value={form.pair}
          onChange={e => setForm(p => ({ ...p, pair: e.target.value.toUpperCase() }))}
          style={{ flex: 1, minWidth: 120 }}
        />
        {["1H", "2H", "4H", "1D"].map(t => (
          <button key={t} onClick={() => setForm(p => ({ ...p, tf: t }))}
            className={`btn btn-sm ${form.tf === t ? "btn-primary" : "btn-ghost"}`}>
            {t}
          </button>
        ))}
        {(["SHORT", "LONG"] as const).map(d => (
          <button key={d} onClick={() => setForm(p => ({ ...p, dir: d }))}
            className="btn btn-sm"
            style={{
              background: form.dir === d ? (d === "LONG" ? "var(--green-bg)" : "var(--red-bg)") : "transparent",
              color: d === "LONG" ? "var(--green)" : "var(--red)",
              border: `1.5px solid ${form.dir === d ? (d === "LONG" ? "var(--green)" : "var(--red)") : "var(--border)"}`,
              fontWeight: form.dir === d ? 600 : 400,
            }}>
            {d}
          </button>
        ))}
      </div>

      {hasCriteria && <div className="flex col gap-2">
        {strategy.criteria.map(c => {
          const isCore = cores.includes(c.id);
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
                  }}>{checked[c.id] ? "✓" : ""}</div>
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
                <div className="text-xs text-2" style={{ padding: "6px 14px 6px 48px" }}>{c.description}</div>
              )}
            </div>
          );
        })}
      </div>}

      <div className="card mt-3" style={{ textAlign: "center", borderColor: verdict.color, borderWidth: 2 }}>
        {hasCriteria && <div style={{ fontSize: 40, fontWeight: 500, color: verdict.color }}>{score}/100</div>}
        <div style={{ fontSize: 15, fontWeight: 500, color: verdict.color, marginTop: 4 }}>{verdict.text}</div>
        {form.pair && <div className="text-sm text-2 mt-2">{form.pair} | {form.dir} | {form.tf}</div>}
      </div>

      <div className="card mt-3">
        <h3 className="text-sm font-500 mb-2">Plan</h3>
        <div className="flex gap-2">
          <div className="grow">
            <label className="text-xs text-2">Planned entry</label>
            <input type="number" step="any" value={form.planned_entry}
              onChange={e => setForm(p => ({ ...p, planned_entry: e.target.value }))} />
          </div>
          <div className="grow">
            <label className="text-xs text-2">Planned stop</label>
            <input type="number" step="any" value={form.planned_stop}
              onChange={e => setForm(p => ({ ...p, planned_stop: e.target.value }))} />
          </div>
          <div className="grow">
            <label className="text-xs text-2">Planned target</label>
            <input type="number" step="any" value={form.planned_target}
              onChange={e => setForm(p => ({ ...p, planned_target: e.target.value }))} />
          </div>
        </div>
        {computedRR != null && (
          <div className="text-xs text-2 mt-2">Planned R:R = {computedRR}</div>
        )}
      </div>

      <div className="card mt-3">
        <h3 className="text-sm font-500 mb-1">Confluences</h3>
        <div className="text-xs text-2 mb-2">
          Free-text tags layered on top of your strategy criteria — e.g. <i>london_open</i>, <i>htf_aligned</i>, <i>30min_reversal</i>. Used later to filter analytics ("when X is present, my win rate is Y").
        </div>
        <ConfluenceInput
          value={confluences}
          onChange={setConfluences}
          suggestions={confluenceSuggestions}
        />
      </div>

      <textarea
        placeholder="Logic / why this trade"
        value={form.notes}
        rows={3}
        className="mt-3"
        onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
        style={{ resize: "vertical" }}
      />

      <button onClick={save} disabled={!form.pair || saving}
        className="btn btn-primary mt-3" style={{ width: "100%" }}>
        {saved ? "Saved!" : saving ? "Saving..." : form.pair ? `Save Plan: ${form.pair} ${form.dir}` : "Enter pair to save"}
      </button>

      <StrategyManager
        open={showStrategies}
        onClose={() => setShowStrategies(false)}
        onSaved={loadStrategies}
      />
    </div>
  );
}
