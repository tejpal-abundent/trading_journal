import { useState } from "react";

interface Props {
  value: string[];
  onChange: (next: string[]) => void;
  suggestions?: string[];
  placeholder?: string;
}

const normalize = (s: string) =>
  s.trim().toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");

export default function ConfluenceInput({ value, onChange, suggestions = [], placeholder }: Props) {
  const [input, setInput] = useState("");

  const add = (raw: string) => {
    const tag = normalize(raw);
    if (tag && !value.includes(tag)) onChange([...value, tag]);
    setInput("");
  };

  const remove = (tag: string) => onChange(value.filter(t => t !== tag));

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      if (input.trim()) add(input);
    } else if (e.key === "Backspace" && !input && value.length) {
      remove(value[value.length - 1]);
    }
  };

  const unused = suggestions.filter(s => !value.includes(s));

  return (
    <div>
      <div className="chip-row" style={{ alignItems: "center" }}>
        {value.map(t => (
          <span key={t} className="chip selected" onClick={() => remove(t)} title="Click to remove">
            {t.replace(/_/g, " ")} ×
          </span>
        ))}
        <input
          value={input}
          placeholder={placeholder || "Add confluence (Enter or , to add)"}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          onBlur={() => input.trim() && add(input)}
          style={{
            border: "none", padding: "4px 8px", background: "transparent",
            minWidth: 200, flex: 1, outline: "none",
          }}
        />
      </div>
      {unused.length > 0 && (
        <div className="text-xs text-2 mt-1">
          <span style={{ marginRight: 6 }}>Recent:</span>
          {unused.slice(0, 12).map(s => (
            <span key={s} className="chip" style={{ marginRight: 4, cursor: "pointer" }} onClick={() => add(s)}>
              + {s.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
