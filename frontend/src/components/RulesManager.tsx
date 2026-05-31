import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, TradingRule } from "../api";

export default function RulesManager() {
  const [rules, setRules] = useState<TradingRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newBody, setNewBody] = useState("");
  const navigate = useNavigate();

  const load = () => api.listRules().then(setRules).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!newTitle.trim()) return;
    await api.createRule({ title: newTitle.trim(), body: newBody });
    setNewTitle(""); setNewBody(""); setAdding(false);
    load();
  };

  const remove = async (id: number) => {
    if (!confirm("Delete this rule?")) return;
    await api.deleteRule(id);
    load();
  };

  if (loading) return <div className="text-2 text-sm">Loading…</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 800 }}>
      <div className="flex between center">
        <h2 style={{ margin: 0 }}>Trading Rules</h2>
        <div className="flex gap-2">
          <button className="btn btn-ghost btn-sm" onClick={() => navigate("/")}>← Back</button>
          <button className="btn btn-primary btn-sm" onClick={() => setAdding(true)}>+ Add rule</button>
        </div>
      </div>
      {adding && (
        <div className="card" style={{ borderLeft: "3px solid var(--blue)" }}>
          <label style={{ display: "block", marginBottom: 8 }}>
            <span className="text-xs text-2">Title</span>
            <input className="input" type="text" value={newTitle} onChange={e => setNewTitle(e.target.value)} style={{ width: "100%" }} />
          </label>
          <label style={{ display: "block", marginBottom: 8 }}>
            <span className="text-xs text-2">Body (optional)</span>
            <textarea className="input" rows={3} value={newBody} onChange={e => setNewBody(e.target.value)} style={{ width: "100%" }} />
          </label>
          <div className="flex gap-2">
            <button className="btn btn-primary btn-sm" disabled={!newTitle.trim()} onClick={add}>Save</button>
            <button className="btn btn-ghost btn-sm" onClick={() => { setAdding(false); setNewTitle(""); setNewBody(""); }}>Cancel</button>
          </div>
        </div>
      )}
      {rules.length === 0 && !adding && (
        <div className="text-2 text-sm">No rules yet. Click + Add rule.</div>
      )}
      {rules.map(r => (
        <RuleEditor key={r.id} rule={r} onChange={load} onDelete={() => remove(r.id)} />
      ))}
    </div>
  );
}

function RuleEditor({ rule, onChange, onDelete }: { rule: TradingRule; onChange: () => void; onDelete: () => void }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(rule.title);
  const [body, setBody] = useState(rule.body);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      await api.updateRule(rule.id, { title, body });
      setEditing(false);
      onChange();
    } finally { setBusy(false); }
  };
  const cancel = () => { setTitle(rule.title); setBody(rule.body); setEditing(false); };

  return (
    <div className="card">
      {editing ? (
        <>
          <label style={{ display: "block", marginBottom: 8 }}>
            <span className="text-xs text-2">Title</span>
            <input className="input" type="text" value={title} onChange={e => setTitle(e.target.value)} style={{ width: "100%" }} />
          </label>
          <label style={{ display: "block", marginBottom: 8 }}>
            <span className="text-xs text-2">Body</span>
            <textarea className="input" rows={4} value={body} onChange={e => setBody(e.target.value)} style={{ width: "100%" }} />
          </label>
          <div className="flex gap-2">
            <button className="btn btn-primary btn-sm" disabled={busy} onClick={save}>Save</button>
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={cancel}>Cancel</button>
          </div>
        </>
      ) : (
        <>
          <div className="flex between center">
            <h3 style={{ margin: 0, fontSize: 15 }}>{rule.title}</h3>
            <div className="flex gap-2">
              <button className="btn btn-ghost btn-sm" onClick={() => setEditing(true)}>Edit</button>
              <button className="btn btn-ghost btn-sm" style={{ color: "var(--red)" }} onClick={onDelete}>Delete</button>
            </div>
          </div>
          {rule.body && <div className="text-sm text-2" style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{rule.body}</div>}
        </>
      )}
    </div>
  );
}
