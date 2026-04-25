import { useState } from "react";
import { labelize } from "../constants/tags";

interface Props {
  options: readonly string[] | string[];
  selected: string[];
  onChange: (next: string[]) => void;
  variant?: "default" | "mistake";
  allowCustom?: boolean;
}

export default function TagChips({ options, selected, onChange, variant = "default", allowCustom = true }: Props) {
  const [adding, setAdding] = useState(false);
  const [custom, setCustom] = useState("");

  const toggle = (tag: string) => {
    if (selected.includes(tag)) onChange(selected.filter(t => t !== tag));
    else onChange([...selected, tag]);
  };

  const addCustom = () => {
    const t = custom.trim().toLowerCase().replace(/\s+/g, "_");
    if (t && !selected.includes(t)) onChange([...selected, t]);
    setCustom(""); setAdding(false);
  };

  const allOptions = Array.from(new Set([...options, ...selected]));

  return (
    <div className="chip-row">
      {allOptions.map(t => (
        <span key={t}
          className={`chip ${variant} ${selected.includes(t) ? "selected" : ""}`}
          onClick={() => toggle(t)}>
          {labelize(t)}
        </span>
      ))}
      {allowCustom && !adding && (
        <span className="chip" onClick={() => setAdding(true)}>+ custom</span>
      )}
      {adding && (
        <span className="chip" style={{ padding: 0 }}>
          <input autoFocus
            value={custom}
            onChange={e => setCustom(e.target.value)}
            onBlur={addCustom}
            onKeyDown={e => { if (e.key === "Enter") addCustom(); if (e.key === "Escape") { setAdding(false); setCustom(""); } }}
            style={{ width: 100, border: "none", padding: "4px 8px", background: "transparent" }} />
        </span>
      )}
    </div>
  );
}
