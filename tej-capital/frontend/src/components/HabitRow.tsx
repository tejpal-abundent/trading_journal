import { useState } from "react";
import { HabitCell } from "./HabitCell";
import type { HabitDefinition } from "../hooks/useHabits";
import "../design/components.css";

export type HabitRowProps = {
  definition: HabitDefinition;
  days: string[];
  entries: Record<string, boolean>;
  streak: number;
  isEditing: boolean;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSetStatus: (date: string, status: boolean) => void;
  onClear: (date: string) => void;
  onRename: (label: string) => void;
  onMove: (direction: "up" | "down") => void;
  onRetire: () => void;
};

export function HabitRow({
  definition, days, entries, streak, isEditing,
  onStartEdit, onCancelEdit, onSetStatus, onClear, onRename, onMove, onRetire,
}: HabitRowProps) {
  const [draftLabel, setDraftLabel] = useState(definition.label);

  // Two-zone cell — see HabitCell. Left click → true, right click → false,
  // click on already-filled cell → clear. No cycle.

  function saveRename() {
    const trimmed = draftLabel.trim();
    if (trimmed && trimmed !== definition.label) onRename(trimmed);
    onCancelEdit();
  }

  return (
    <div className="habit-row">
      {isEditing ? (
        <div className="habit-row__edit">
          <input
            className="field__input habit-row__edit-input"
            value={draftLabel}
            autoFocus
            onChange={(e) => setDraftLabel(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") saveRename();
              if (e.key === "Escape") onCancelEdit();
            }}
          />
          <div className="habit-row__edit-actions">
            <button type="button" className="habit-row__icon-btn" onClick={() => onMove("up")} aria-label="Move up">
              ↑
            </button>
            <button type="button" className="habit-row__icon-btn" onClick={() => onMove("down")} aria-label="Move down">
              ↓
            </button>
            <button type="button" className="habit-row__icon-btn" onClick={saveRename} aria-label="Save">
              ✓
            </button>
            <button type="button" className="habit-row__icon-btn" onClick={onRetire} aria-label="Remove habit">
              ×
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="habit-row__label" onClick={onStartEdit}>
          {definition.label}
        </button>
      )}

      <div className="habit-row__cells">
        {days.map((day) => (
          <HabitCell
            key={day}
            state={entries[day]}
            label={`${definition.label} — ${day}`}
            onSetTrue={() => onSetStatus(day, true)}
            onSetFalse={() => onSetStatus(day, false)}
            onClear={() => onClear(day)}
          />
        ))}
      </div>

      <div className="habit-row__streak">{streak > 0 ? `${streak}d` : "—"}</div>
    </div>
  );
}
