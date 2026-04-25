import { useState } from "react";
import { api, Trade } from "../api";
import { EMOTION_TAGS } from "../constants/tags";
import TagChips from "./TagChips";

interface Props {
  trade: Trade;
  onSaved: (t: Trade) => void;
  onCancel: () => void;
}

export default function SkipTradeForm({ trade, onSaved, onCancel }: Props) {
  const [reason, setReason] = useState("");
  const [emotions, setEmotions] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!reason.trim() || saving) return;
    setSaving(true);
    try {
      const t = await api.skipTrade(trade.id, { skip_reason: reason, emotions_entry: emotions });
      onSaved(t);
    } catch (err) {
      alert("Failed: " + (err instanceof Error ? err.message : "Unknown"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex col gap-2">
      <div>
        <label className="text-xs text-2">Why did you skip this trade?</label>
        <input value={reason} onChange={e => setReason(e.target.value)} placeholder="e.g. News in 1h" />
      </div>
      <div>
        <label className="text-xs text-2">Feelings</label>
        <TagChips options={EMOTION_TAGS} selected={emotions} onChange={setEmotions} />
      </div>
      <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-sm btn-ghost" onClick={onCancel}>Cancel</button>
        <button className="btn btn-sm btn-primary" onClick={save} disabled={saving || !reason.trim()}>
          {saving ? "Saving..." : "Mark as Skipped"}
        </button>
      </div>
    </div>
  );
}
