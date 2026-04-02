import { useState, useEffect } from "react";
import { api, Trade } from "../api";

export default function TradeList() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [filter, setFilter] = useState("all");
  const [editing, setEditing] = useState<Trade | null>(null);
  const [form, setForm] = useState({ status: "", entry_price: "", exit_price: "", stop_loss: "", take_profit: "", pnl: "", pnl_percent: "", rr_achieved: "", lessons: "" });
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const data = await api.listTrades(filter === "all" ? undefined : filter);
    setTrades(data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [filter]);

  const openEdit = (t: Trade) => {
    setEditing(t);
    setForm({
      status: t.status,
      entry_price: t.entry_price?.toString() || "",
      exit_price: t.exit_price?.toString() || "",
      stop_loss: t.stop_loss?.toString() || "",
      take_profit: t.take_profit?.toString() || "",
      pnl: t.pnl?.toString() || "",
      pnl_percent: t.pnl_percent?.toString() || "",
      rr_achieved: t.rr_achieved?.toString() || "",
      lessons: t.lessons || "",
    });
  };

  const [saving, setSaving] = useState(false);

  const saveResult = async () => {
    if (!editing || saving) return;
    setSaving(true);
    try {
      const data: Record<string, unknown> = { status: form.status, lessons: form.lessons };
      if (form.entry_price) data.entry_price = parseFloat(form.entry_price);
      if (form.exit_price) data.exit_price = parseFloat(form.exit_price);
      if (form.stop_loss) data.stop_loss = parseFloat(form.stop_loss);
      if (form.take_profit) data.take_profit = parseFloat(form.take_profit);
      if (form.pnl) data.pnl = parseFloat(form.pnl);
      if (form.pnl_percent) data.pnl_percent = parseFloat(form.pnl_percent);
      if (form.rr_achieved) data.rr_achieved = parseFloat(form.rr_achieved);
      await api.updateTrade(editing.id, data as Partial<Trade>);
      setEditing(null);
      load();
    } catch (e) {
      alert("Failed to save: " + (e instanceof Error ? e.message : "Unknown error"));
    } finally {
      setSaving(false);
    }
  };

  const deleteTrade = async (id: number) => {
    if (!confirm("Delete this trade?")) return;
    await api.deleteTrade(id);
    load();
  };

  const statusTag = (s: string) => {
    const cls = s === "win" ? "tag-green" : s === "loss" ? "tag-red" : s === "breakeven" ? "tag-yellow" : "tag-blue";
    return <span className={`tag ${cls}`}>{s.toUpperCase()}</span>;
  };

  const scoreBorder = (score: number) =>
    score >= 85 ? "var(--green)" : score >= 70 ? "var(--yellow)" : score >= 55 ? "#D85A30" : "var(--red)";

  return (
    <div>
      <div className="flex gap-2 center between mb-3">
        <h2 style={{ fontSize: 16 }}>Trade Log</h2>
        <div className="flex gap-2">
          {["all", "open", "win", "loss"].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`btn btn-sm ${filter === f ? "btn-primary" : "btn-ghost"}`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-2 text-sm">Loading...</p>
      ) : trades.length === 0 ? (
        <p className="text-2 text-sm">No trades yet. Go log your first setup!</p>
      ) : (
        trades.map(t => (
          <div key={t.id} className="card" style={{ borderLeft: `3px solid ${scoreBorder(t.setup_score)}` }}>
            <div className="flex between center">
              <div className="flex gap-2 center">
                <span className="font-500">{t.pair}</span>
                <span className={`tag ${t.direction === "LONG" ? "tag-green" : "tag-red"}`}>{t.direction}</span>
                <span className="tag tag-blue">{t.timeframe}</span>
                {statusTag(t.status)}
              </div>
              <span className="font-500">{t.setup_score}/100</span>
            </div>

            <div className="text-xs text-2 mt-2">
              {new Date(t.created_at).toLocaleString()}
              {t.notes && <span> &mdash; {t.notes}</span>}
            </div>

            {t.status !== "open" && t.pnl !== null && (
              <div className="flex gap-3 mt-2 text-sm">
                <span>P/L: <b style={{ color: t.pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                  {t.pnl >= 0 ? "+" : ""}{t.pnl}
                </b></span>
                {t.pnl_percent !== null && <span>{t.pnl_percent >= 0 ? "+" : ""}{t.pnl_percent}%</span>}
                {t.rr_achieved !== null && <span>R:R {t.rr_achieved}</span>}
              </div>
            )}

            {t.lessons && (
              <div className="text-xs text-2 mt-2" style={{ fontStyle: "italic" }}>
                Lessons: {t.lessons}
              </div>
            )}

            <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
              <button onClick={() => openEdit(t)} className="btn btn-sm btn-ghost">
                {t.status === "open" ? "Add Result" : "Edit"}
              </button>
              <button onClick={() => deleteTrade(t.id)} className="btn btn-sm btn-ghost"
                style={{ color: "var(--red)" }}>Delete</button>
            </div>
          </div>
        ))
      )}

      {editing && (
        <div className="modal-overlay" onClick={() => setEditing(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Trade Result: {editing.pair} {editing.direction}</h3>

            <div className="flex col gap-2">
              <label className="text-xs text-2">Status</label>
              <select value={form.status} onChange={e => setForm(p => ({ ...p, status: e.target.value }))}>
                <option value="open">Open</option>
                <option value="win">Win</option>
                <option value="loss">Loss</option>
                <option value="breakeven">Breakeven</option>
                <option value="skipped">Skipped</option>
              </select>

              <div className="flex gap-2">
                <div className="grow">
                  <label className="text-xs text-2">Entry Price</label>
                  <input type="number" step="any" value={form.entry_price}
                    onChange={e => setForm(p => ({ ...p, entry_price: e.target.value }))} />
                </div>
                <div className="grow">
                  <label className="text-xs text-2">Exit Price</label>
                  <input type="number" step="any" value={form.exit_price}
                    onChange={e => setForm(p => ({ ...p, exit_price: e.target.value }))} />
                </div>
              </div>

              <div className="flex gap-2">
                <div className="grow">
                  <label className="text-xs text-2">Stop Loss</label>
                  <input type="number" step="any" value={form.stop_loss}
                    onChange={e => setForm(p => ({ ...p, stop_loss: e.target.value }))} />
                </div>
                <div className="grow">
                  <label className="text-xs text-2">Take Profit</label>
                  <input type="number" step="any" value={form.take_profit}
                    onChange={e => setForm(p => ({ ...p, take_profit: e.target.value }))} />
                </div>
              </div>

              <div className="flex gap-2">
                <div className="grow">
                  <label className="text-xs text-2">P/L ($)</label>
                  <input type="number" step="any" value={form.pnl}
                    onChange={e => setForm(p => ({ ...p, pnl: e.target.value }))} />
                </div>
                <div className="grow">
                  <label className="text-xs text-2">P/L %</label>
                  <input type="number" step="any" value={form.pnl_percent}
                    onChange={e => setForm(p => ({ ...p, pnl_percent: e.target.value }))} />
                </div>
                <div className="grow">
                  <label className="text-xs text-2">R:R</label>
                  <input type="number" step="any" value={form.rr_achieved}
                    onChange={e => setForm(p => ({ ...p, rr_achieved: e.target.value }))} />
                </div>
              </div>

              <label className="text-xs text-2">Lessons Learned</label>
              <textarea value={form.lessons} rows={3}
                placeholder="What did you learn from this trade?"
                onChange={e => setForm(p => ({ ...p, lessons: e.target.value }))} />

              <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
                <button onClick={() => setEditing(null)} className="btn btn-sm btn-ghost">Cancel</button>
                <button onClick={saveResult} disabled={saving} className="btn btn-sm btn-primary">{saving ? "Saving..." : "Save Result"}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
