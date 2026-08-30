import clsx from "clsx";
import "../design/components.css";

/** undefined = unanswered (empty state). */
export type HabitCellState = boolean | undefined;

/** empty -> true -> false -> empty */
export function nextHabitCellState(current: HabitCellState): HabitCellState {
  if (current === undefined) return true;
  if (current === true) return false;
  return undefined;
}

export function HabitCell({ state, onClick, label }: {
  state: HabitCellState;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className={clsx(
        "habit-cell",
        state === true && "habit-cell--true",
        state === false && "habit-cell--false",
        state === undefined && "habit-cell--empty",
      )}
      onClick={onClick}
      aria-label={label}
      aria-pressed={state === true}
      title={label}
    >
      {state === true && (
        <svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true">
          <path
            d="M3 8.5L6.3 12L13 4.2"
            fill="none" stroke="currentColor" strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round"
          />
        </svg>
      )}
      {state === false && (
        <svg viewBox="0 0 16 16" width="9" height="9" aria-hidden="true">
          <path
            d="M4 4L12 12M12 4L4 12"
            fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
          />
        </svg>
      )}
    </button>
  );
}
