import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, TradingRule } from "../api";

export default function RulesCard() {
  const [rules, setRules] = useState<TradingRule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listRules().then(setRules).finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (rules.length === 0) {
    return (
      <div className="card">
        <div className="flex between center">
          <h3 style={{ margin: 0 }}>My Rules</h3>
          <Link to="/rules" className="text-xs text-2">Manage</Link>
        </div>
        <div className="text-2 text-sm" style={{ marginTop: 8 }}>No rules yet. Add some.</div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex between center" style={{ marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>My Rules</h3>
        <Link to="/rules" className="text-xs text-2">Manage</Link>
      </div>
      <ol style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 12 }}>
        {rules.map(r => (
          <li key={r.id}>
            <div className="font-500" style={{ fontSize: 14 }}>{r.title}</div>
            {r.body && <div className="text-xs text-2" style={{ marginTop: 2, whiteSpace: "pre-wrap" }}>{r.body}</div>}
          </li>
        ))}
      </ol>
    </div>
  );
}
