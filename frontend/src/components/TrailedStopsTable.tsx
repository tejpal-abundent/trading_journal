import { useState } from "react";
import { Trade, TrailedStop, api } from "../api";

interface Props {
  trade: Trade;
  onChange: (t: Trade) => void;
}

export default function TrailedStopsTable({ trade, onChange }: Props) {
  const [newPrice, setNewPrice] = useState("");
  const [newNote, setNewNote] = useState("");
  const [busy, setBusy] = useState(false);

  const trails = trade.trailed_stops || [];
  const penultimateIdx = trade.status === "win" && trails.length >= 2 ? trails.length - 2 : -1;

  const add = async () => {
    const price = parseFloat(newPrice);
    if (Number.isNaN(price)) return;
    setBusy(true);
    try {
      const updated = await api.addTrail(trade.id, price, newNote || undefined);
      onChange(updated);
      setNewPrice(""); setNewNote("");
    } finally { setBusy(false); }
  };

  const remove = async (idx: number) => {
    if (!confirm("Remove this trail?")) return;
    setBusy(true);
    try {
      const updated = await api.deleteTrail(trade.id, idx);
      onChange(updated);
    } finally { setBusy(false); }
  };

  return (
    <div className="card">
      <div className="flex between center" style={{ marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Trailed stops ({trails.length})</h3>
      </div>

      {trails.length === 0 ? (
        <div className="text-2 text-xs" style={{ marginBottom: 8 }}>No trails yet.</div>
      ) : (
        <table style={{ width: "100%", fontSize: 14, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left" }}>
              <th style={{ padding: "4px 8px" }}>#</th>
              <th style={{ padding: "4px 8px" }}>Price</th>
              <th style={{ padding: "4px 8px" }}>Time</th>
              <th style={{ padding: "4px 8px" }}>Note</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {trails.map((s: TrailedStop, idx: number) => {
              const isPenultimate = idx === penultimateIdx;
              return (
                <tr key={idx} style={{
                  background: isPenultimate ? "var(--yellow-bg, #fef3c7)" : "transparent",
                }}>
                  <td style={{ padding: "4px 8px" }}>{idx + 1}</td>
                  <td style={{ padding: "4px 8px" }}>{s.price}</td>
                  <td style={{ padding: "4px 8px" }} className="text-2 text-xs">
                    {new Date(s.at).toLocaleString()}
                  </td>
                  <td style={{ padding: "4px 8px" }}>{s.note ?? ""}</td>
                  <td style={{ padding: "4px 8px", textAlign: "right" }}>
                    <button className="btn btn-sm btn-ghost" disabled={busy} onClick={() => remove(idx)}>×</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {trade.status === "entered" && (
        <div className="flex gap-2 center" style={{ marginTop: 8 }}>
          <input
            className="input"
            type="number"
            placeholder="price"
            value={newPrice}
            onChange={e => setNewPrice(e.target.value)}
            style={{ width: 120 }}
          />
          <input
            className="input"
            type="text"
            placeholder="note (optional)"
            value={newNote}
            onChange={e => setNewNote(e.target.value)}
            style={{ flex: 1 }}
          />
          <button className="btn btn-sm btn-primary" disabled={busy || !newPrice} onClick={add}>
            + Add trail
          </button>
        </div>
      )}

      {penultimateIdx >= 0 && trade.r_locked_at_penultimate_trail != null && (
        <div className="text-xs text-2" style={{ marginTop: 8 }}>
          The highlighted row is the -1th trail. R locked here: <b>{trade.r_locked_at_penultimate_trail}R</b>.
        </div>
      )}
    </div>
  );
}
