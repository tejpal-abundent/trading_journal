import { ChangeEvent } from "react";

interface Props {
  label: string;
  value: string | number | null | undefined;
  type?: "text" | "number" | "textarea";
  editing: boolean;
  onChange: (v: string) => void;
  width?: number | string;
  placeholder?: string;
}

/**
 * A simple label + (read-only display OR input) widget. Used heavily in
 * TradeDetailPage's edit mode to keep the markup uniform.
 */
export default function EditableField({
  label, value, type = "text", editing, onChange, width, placeholder,
}: Props) {
  const display = value === null || value === undefined || value === "" ? "—" : String(value);

  if (!editing) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <span className="text-xs text-2">{label}</span>
        <span className="text-sm">{display}</span>
      </div>
    );
  }

  const onInput = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(e.target.value);

  if (type === "textarea") {
    return (
      <label style={{ display: "flex", flexDirection: "column", gap: 2, width }}>
        <span className="text-xs text-2">{label}</span>
        <textarea
          className="input"
          value={value === null || value === undefined ? "" : String(value)}
          onChange={onInput}
          placeholder={placeholder}
          rows={3}
        />
      </label>
    );
  }

  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 2, width }}>
      <span className="text-xs text-2">{label}</span>
      <input
        className="input"
        type={type}
        value={value === null || value === undefined ? "" : String(value)}
        onChange={onInput}
        placeholder={placeholder}
      />
    </label>
  );
}
