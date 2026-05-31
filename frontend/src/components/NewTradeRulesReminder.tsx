import { useEffect, useState } from "react";
import { api, TradingRule } from "../api";

export default function NewTradeRulesReminder() {
  const [rules, setRules] = useState<TradingRule[]>([]);
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [open, setOpen] = useState(true);

  useEffect(() => {
    api.listRules().then(setRules);
  }, []);

  if (rules.length === 0) return null;

  const toggle = (id: number) => {
    setChecked(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const allChecked = checked.size === rules.length;

  return (
    <div className="card" style={{ borderLeft: `3px solid ${allChecked ? "var(--green)" : "var(--yellow)"}`, marginBottom: 12 }}>
      <div className="flex between center" style={{ cursor: "pointer" }} onClick={() => setOpen(!open)}>
        <h3 style={{ margin: 0, fontSize: 14 }}>
          Pre-trade rule check ({checked.size}/{rules.length})
        </h3>
        <span className="text-xs text-2">{open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
          {rules.map(r => (
            <label key={r.id} style={{ display: "flex", gap: 8, alignItems: "flex-start", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={checked.has(r.id)}
                onChange={() => toggle(r.id)}
                style={{ marginTop: 3 }}
              />
              <div>
                <div className="text-sm font-500">{r.title}</div>
                {r.body && <div className="text-xs text-2" style={{ whiteSpace: "pre-wrap" }}>{r.body}</div>}
              </div>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
