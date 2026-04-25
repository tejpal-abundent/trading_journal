import { useEffect, useState } from "react";
import { api, Strategy } from "../api";

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

interface CritDraft { id: string; label: string; points: number; category: string; description: string; is_core: boolean }

export default function StrategyManager({ open, onClose, onSaved }: Props) {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [editing, setEditing] = useState<Strategy | null>(null);
  const [name, setName] = useState("");
  const [crits, setCrits] = useState<CritDraft[]>([]);
  const [saving, setSaving] = useState(false);
  const [creatingNew, setCreatingNew] = useState(false);

  const loadAll = async () => {
    const s = await api.listStrategies();
    setStrategies(s);
  };

  useEffect(() => { if (open) loadAll(); }, [open]);

  const startNew = () => {
    setEditing(null);
    setCreatingNew(true);
    setName("New Strategy");
    setCrits([]);
  };

  const startEdit = (s: Strategy) => {
    setEditing(s);
    setCreatingNew(false);
    setName(s.name);
    setCrits(s.criteria.map(c => ({
      ...c, is_core: s.is_core_required.includes(c.id),
    })));
  };

  const cancel = () => { setEditing(null); setCreatingNew(false); setName(""); setCrits([]); };

  const addCrit = () => {
    setCrits(p => [...p, {
      id: `c${p.length + 1}`,
      label: "",
      points: 5,
      category: "Quality",
      description: "",
      is_core: false,
    }]);
  };

  const updateCrit = (i: number, patch: Partial<CritDraft>) => {
    setCrits(p => p.map((c, idx) => idx === i ? { ...c, ...patch } : c));
  };

  const removeCrit = (i: number) => setCrits(p => p.filter((_, idx) => idx !== i));

  const save = async () => {
    if (!name.trim() || saving) return;
    setSaving(true);
    try {
      const payload = {
        name: name.trim(),
        criteria: crits.map(({ is_core: _ic, ...c }) => c),
        is_core_required: crits.filter(c => c.is_core).map(c => c.id),
      };
      if (editing) {
        await api.updateStrategy(editing.id, payload);
      } else {
        await api.createStrategy(payload);
      }
      await loadAll();
      onSaved();
      cancel();
    } catch (e) {
      alert("Save failed: " + (e instanceof Error ? e.message : "Unknown"));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (s: Strategy) => {
    if (!confirm(`Delete strategy "${s.name}"?`)) return;
    try {
      await api.deleteStrategy(s.id);
      await loadAll();
      onSaved();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  if (!open) return null;

  const inEditMode = editing != null || creatingNew;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 720 }}>
        <h3>Strategies</h3>

        {!inEditMode ? (
          <>
            <div className="flex col gap-2 mt-2">
              {strategies.map(s => (
                <div key={s.id} className="card flex between center" style={{ padding: "8px 12px" }}>
                  <div>
                    <b>{s.name}</b>
                    <span className="text-xs text-2 ml-2">{s.criteria.length} criteria</span>
                  </div>
                  <div className="flex gap-2">
                    <button className="btn btn-sm btn-ghost" onClick={() => startEdit(s)}>Edit</button>
                    <button className="btn btn-sm btn-ghost" style={{ color: "var(--red)" }} onClick={() => remove(s)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-3" style={{ justifyContent: "flex-end" }}>
              <button className="btn btn-sm btn-ghost" onClick={onClose}>Close</button>
              <button className="btn btn-sm btn-primary" onClick={startNew}>+ New strategy</button>
            </div>
          </>
        ) : (
          <>
            <div className="mt-2">
              <label className="text-xs text-2">Name</label>
              <input value={name} onChange={e => setName(e.target.value)} />
            </div>
            <div className="mt-3">
              <div className="flex between center mb-2">
                <span className="text-sm font-500">Criteria</span>
                <button className="btn btn-sm btn-ghost" onClick={addCrit}>+ Add criterion</button>
              </div>
              {crits.map((c, i) => (
                <div key={i} className="card" style={{ padding: 10, marginBottom: 8 }}>
                  <div className="flex gap-2">
                    <input style={{ flex: 1 }} placeholder="Criterion label"
                      value={c.label} onChange={e => updateCrit(i, { label: e.target.value })} />
                    <input style={{ width: 70 }} type="number" min={0} max={100}
                      value={c.points} onChange={e => updateCrit(i, { points: parseInt(e.target.value || "0") })} />
                  </div>
                  <div className="flex gap-2 mt-1">
                    <input style={{ width: 110 }} placeholder="id" value={c.id}
                      onChange={e => updateCrit(i, { id: e.target.value.replace(/\s+/g, "_") })} />
                    <input style={{ width: 130 }} placeholder="Category" value={c.category}
                      onChange={e => updateCrit(i, { category: e.target.value })} />
                    <label className="flex center gap-1 text-xs">
                      <input type="checkbox" checked={c.is_core}
                        onChange={e => updateCrit(i, { is_core: e.target.checked })} />
                      Core
                    </label>
                    <button className="btn btn-sm btn-ghost" style={{ color: "var(--red)" }}
                      onClick={() => removeCrit(i)}>Remove</button>
                  </div>
                  <input className="mt-1" placeholder="Description (shown on tap of ?)"
                    value={c.description} onChange={e => updateCrit(i, { description: e.target.value })} />
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-3" style={{ justifyContent: "flex-end" }}>
              <button className="btn btn-sm btn-ghost" onClick={cancel}>Cancel</button>
              <button className="btn btn-sm btn-primary" onClick={save} disabled={saving}>
                {saving ? "Saving..." : "Save"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
