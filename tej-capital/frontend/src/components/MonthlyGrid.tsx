import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import "../design/components.css";

export type MonthlyCell = {
  /** Fractional return, e.g. 0.0123 = 1.23%. Null/undefined = no trading that month. */
  value: number | null;
  n?: number;
};

export type MonthlyGridRow = {
  year: number;
  /** 12 entries, January first. */
  months: MonthlyCell[];
};

export type MonthlyGridProps = {
  rows: MonthlyGridRow[];
  /** |value| that reaches full color saturation. Default 8%. */
  scaleMax?: number;
};

const MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * Year x month table. Cells are colored by return sign with saturation
 * scaled to |value|. Empty (no-trading) months render as "—" on --ground-2,
 * never "0%" (R3).
 */
export function MonthlyGrid({ rows, scaleMax = 0.08 }: MonthlyGridProps) {
  return (
    <table className="monthly-grid">
      <thead>
        <tr>
          <th className="monthly-grid__year-header" />
          {MONTH_LABELS.map((m) => (
            <th key={m}>{m}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.year}>
            <th className="monthly-grid__year">{row.year}</th>
            {row.months.map((cell, i) => {
              const ym = `${row.year}-${String(i + 1).padStart(2, "0")}`;

              if (cell.value == null) {
                return (
                  <td key={ym} className="monthly-grid__cell monthly-grid__cell--empty">
                    —
                  </td>
                );
              }

              const style: CSSProperties = {};
              let toneClass = "monthly-grid__cell--flat";
              if (cell.value > 0) {
                toneClass = "monthly-grid__cell--gain";
                const pct = Math.min(100, Math.max(25, (Math.abs(cell.value) / scaleMax) * 100));
                style.backgroundColor = `color-mix(in srgb, var(--gain) ${pct}%, var(--gain-soft))`;
                style.color = "var(--gain)";
              } else if (cell.value < 0) {
                toneClass = "monthly-grid__cell--loss";
                const pct = Math.min(100, Math.max(25, (Math.abs(cell.value) / scaleMax) * 100));
                style.backgroundColor = `color-mix(in srgb, var(--loss) ${pct}%, var(--loss-soft))`;
                style.color = "var(--loss)";
              }

              return (
                <td key={ym} className={`monthly-grid__cell ${toneClass}`} style={style}>
                  <Link to={`/tearsheet/${ym}`}>{(cell.value * 100).toFixed(1)}%</Link>
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
