import { PartialExit } from "../api";
import { PARTIAL_EXIT_REASONS, labelize } from "../constants/tags";

interface Props {
  value: PartialExit[];
  onChange: (next: PartialExit[]) => void;
}

export default function PartialExits({ value, onChange }: Props) {
  const update = (i: number, patch: Partial<PartialExit>) => {
    onChange(value.map((p, idx) => idx === i ? { ...p, ...patch } : p));
  };
  const remove = (i: number) => onChange(value.filter((_, idx) => idx !== i));
  const add = () => onChange([...value, { price: 0, size_pct: 50, reason: "took_profit" }]);

  return (
    <div className="flex col gap-1">
      {value.map((p, i) => (
        <div key={i} className="flex gap-1 center">
          <input type="number" step="any" placeholder="price" value={p.price || ""}
            onChange={e => update(i, { price: parseFloat(e.target.value) || 0 })} style={{ width: 100 }} />
          <input type="number" step="any" placeholder="size %" value={p.size_pct || ""}
            onChange={e => update(i, { size_pct: parseFloat(e.target.value) || 0 })} style={{ width: 80 }} />
          <select value={p.reason} onChange={e => update(i, { reason: e.target.value as PartialExit["reason"] })}>
            {PARTIAL_EXIT_REASONS.map(r => <option key={r} value={r}>{labelize(r)}</option>)}
          </select>
          <button className="btn btn-sm btn-ghost" onClick={() => remove(i)} style={{ color: "var(--red)" }}>×</button>
        </div>
      ))}
      <button className="btn btn-sm btn-ghost" onClick={add} style={{ alignSelf: "flex-start" }}>+ Add partial exit</button>
    </div>
  );
}
