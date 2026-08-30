import clsx from "clsx";
import "../design/components.css";

/** undefined = unanswered (empty state). */
export type HabitCellState = boolean | undefined;

/**
 * Empty cell shows BOTH ✓ and ✗ as two independently clickable halves.
 * Filled cell (either state) is a single button whose click clears back
 * to empty. No hidden three-state cycle — every click has an obvious effect.
 */
export function HabitCell({
  state,
  onSetTrue,
  onSetFalse,
  onClear,
  label,
}: {
  state: HabitCellState;
  onSetTrue: () => void;
  onSetFalse: () => void;
  onClear: () => void;
  label: string;
}) {
  if (state === true) {
    return (
      <button
        type="button"
        className="habit-cell habit-cell--true"
        onClick={onClear}
        aria-label={`${label} — marked done. Click to clear.`}
        title={`${label} — done. Click to clear.`}
      >
        <CheckSvg />
      </button>
    );
  }
  if (state === false) {
    return (
      <button
        type="button"
        className="habit-cell habit-cell--false"
        onClick={onClear}
        aria-label={`${label} — marked missed. Click to clear.`}
        title={`${label} — missed. Click to clear.`}
      >
        <CrossSvg />
      </button>
    );
  }
  return (
    <div className="habit-cell habit-cell--empty" role="group" aria-label={label}>
      <button
        type="button"
        className={clsx("habit-cell__half", "habit-cell__half--yes")}
        onClick={onSetTrue}
        aria-label={`${label} — mark done`}
        title="Mark done"
      >
        <CheckSvg />
      </button>
      <button
        type="button"
        className={clsx("habit-cell__half", "habit-cell__half--no")}
        onClick={onSetFalse}
        aria-label={`${label} — mark missed`}
        title="Mark missed"
      >
        <CrossSvg />
      </button>
    </div>
  );
}

function CheckSvg() {
  return (
    <svg viewBox="0 0 16 16" width="10" height="10" aria-hidden="true">
      <path
        d="M3 8.5L6.3 12L13 4.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CrossSvg() {
  return (
    <svg viewBox="0 0 16 16" width="9" height="9" aria-hidden="true">
      <path
        d="M4 4L12 12M12 4L4 12"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
