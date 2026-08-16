import { useState } from "react";
import "../design/components.css";

export type MetricGroupItem = {
  key: string;
  label: string;
  /** One-line plain-English explainer shown under the label (Brief §4.4). */
  explainer: string;
  value: string;
  n: number;
};

/**
 * Collapsible section of metric rows. `--ground-2` background, 1px
 * `--ground-3` border, caret rotates open/closed. Used to hold the
 * Returns / Risk / Risk-Adjusted / Statistical Validity / Trades /
 * Discipline groups on Performance (Task 27 design system contract).
 */
export function MetricGroup({
  title,
  items,
  defaultOpen = false,
}: {
  title: string;
  items: MetricGroupItem[];
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="metric-group">
      <button
        type="button"
        className="metric-group__header"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className={`metric-group__caret${open ? " metric-group__caret--open" : ""}`} aria-hidden="true">
          &#9656;
        </span>
        <span className="metric-group__title">{title}</span>
      </button>
      {open && (
        <div className="metric-group__body">
          {items.map((item) => (
            <div className="metric-group__row" key={item.key}>
              <div className="metric-group__row-label">
                {item.label}
                <div className="metric-group__row-explainer">{item.explainer}</div>
              </div>
              <div className="metric-group__row-value">{item.value}</div>
              <div className="metric-group__row-n">N={item.n}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
