import { useState } from "react";
import { api } from "../api";

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved: (balance: number) => void;
  current: number | null;
}

export default function AccountBalanceModal({ open, onClose, onSaved, current }: Props) {
  const [balance, setBalance] = useState(current ? String(current) : "");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const save = async () => {
    const b = parseFloat(balance);
    if (!isFinite(b) || saving) return;
    setSaving(true);
    try {
      await api.createSnapshot({ balance: b, note });
      onSaved(b);
      onClose();
    } catch (e) {
      alert("Save failed: " + (e instanceof Error ? e.message : "Unknown"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 380 }}>
        <h3>Update account balance</h3>
        <div className="flex col gap-2 mt-2">
          <label className="text-xs text-2">Balance ($)</label>
          <input type="number" step="any" value={balance}
            onChange={e => setBalance(e.target.value)} autoFocus />
          <label className="text-xs text-2">Note (optional)</label>
          <input value={note} onChange={e => setNote(e.target.value)} placeholder="e.g. Deposit $1000" />
          <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
            <button className="btn btn-sm btn-ghost" onClick={onClose}>Cancel</button>
            <button className="btn btn-sm btn-primary" onClick={save} disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
