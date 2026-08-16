import { useState, type CSSProperties } from "react";
import "../design/components.css";

export type YearLedgerMark = {
  /** ISO date, YYYY-MM-DD */
  date: string;
  return_pct: number | null;
  pnl?: number | null;
  trades_closed?: number | null;
  note?: string | null;
};

export type YearLedgerProps = {
  year: number;
  marks: YearLedgerMark[];
  /** |return_pct| that reaches full color saturation. Default 3%. */
  scaleMax?: number;
};

type Cell = {
  date: Date;
  key: string;
  inYear: boolean;
  mark?: YearLedgerMark;
};

function toKey(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function buildWeeks(year: number, byDate: Map<string, YearLedgerMark>): Cell[][] {
  const jan1 = new Date(Date.UTC(year, 0, 1));
  const dec31 = new Date(Date.UTC(year, 11, 31));

  const start = new Date(jan1);
  start.setUTCDate(start.getUTCDate() - start.getUTCDay());

  const end = new Date(dec31);
  end.setUTCDate(end.getUTCDate() + (6 - end.getUTCDay()));

  const weeks: Cell[][] = [];
  const cursor = new Date(start);
  while (cursor <= end) {
    const week: Cell[] = [];
    for (let d = 0; d < 7; d++) {
      const key = toKey(cursor);
      week.push({
        date: new Date(cursor),
        key,
        inYear: cursor.getUTCFullYear() === year,
        mark: byDate.get(key),
      });
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    weeks.push(week);
  }
  return weeks;
}

/**
 * 53x7 grid of 12px squares, one per calendar day. Empty (unmarked) squares
 * are transparent with a 1px --ground-3 outline only — R3: never rendered
 * with gain-soft/loss-soft, which would read as "flat" instead of "unmarked".
 * Colored squares scale saturation to |return|.
 */
export function YearLedger({ year, marks, scaleMax = 0.03 }: YearLedgerProps) {
  const [hover, setHover] = useState<{ cell: Cell; x: number; y: number } | null>(null);

  const byDate = new Map(marks.map((m) => [m.date, m]));
  const weeks = buildWeeks(year, byDate);

  return (
    <div className="year-ledger">
      <div className="year-ledger__grid">
        {weeks.map((week, wi) => (
          <div key={wi} className="year-ledger__week">
            {week.map((cell) => {
              if (!cell.inYear) {
                return (
                  <div
                    key={cell.key}
                    className="year-ledger__cell year-ledger__cell--pad"
                    aria-hidden="true"
                  />
                );
              }

              const m = cell.mark;
              const hasReturn = m?.return_pct != null;
              const style: CSSProperties = {};
              let tone: "" | "gain" | "loss" | "flat" = "";

              if (hasReturn) {
                const r = m!.return_pct as number;
                if (r > 0) {
                  tone = "gain";
                  const pct = Math.min(100, Math.max(20, (Math.abs(r) / scaleMax) * 100));
                  style.backgroundColor = `color-mix(in srgb, var(--gain) ${pct}%, var(--ground-2))`;
                } else if (r < 0) {
                  tone = "loss";
                  const pct = Math.min(100, Math.max(20, (Math.abs(r) / scaleMax) * 100));
                  style.backgroundColor = `color-mix(in srgb, var(--loss) ${pct}%, var(--ground-2))`;
                } else {
                  tone = "flat";
                }
              }

              return (
                <div
                  key={cell.key}
                  className={tone ? `year-ledger__cell year-ledger__cell--${tone}` : "year-ledger__cell"}
                  style={style}
                  data-marked={hasReturn}
                  data-date={cell.key}
                  onMouseEnter={(e) => setHover({ cell, x: e.clientX, y: e.clientY })}
                  onMouseMove={(e) => setHover({ cell, x: e.clientX, y: e.clientY })}
                  onMouseLeave={() => setHover(null)}
                />
              );
            })}
          </div>
        ))}
      </div>
      {hover?.cell.mark && (
        <div
          className="year-ledger__tooltip"
          style={{ left: hover.x + 12, top: hover.y + 12 }}
        >
          <div className="year-ledger__tooltip-date">{hover.cell.key}</div>
          <div className="year-ledger__tooltip-row">
            {hover.cell.mark.return_pct != null ? `${(hover.cell.mark.return_pct * 100).toFixed(2)}%` : "—"}
          </div>
          {hover.cell.mark.pnl != null && (
            <div className="year-ledger__tooltip-row">
              {hover.cell.mark.pnl >= 0 ? "+" : ""}
              {hover.cell.mark.pnl.toFixed(2)}
            </div>
          )}
          {hover.cell.mark.trades_closed != null && (
            <div className="year-ledger__tooltip-row">{hover.cell.mark.trades_closed} trades closed</div>
          )}
          {hover.cell.mark.note && <div className="year-ledger__tooltip-row">{hover.cell.mark.note}</div>}
        </div>
      )}
    </div>
  );
}
