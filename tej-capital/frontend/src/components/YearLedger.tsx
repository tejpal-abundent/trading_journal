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
  /** Render a caption row of month abbreviations above the grid. */
  showMonthLabels?: boolean;
  /** Render M / W / F row labels to the left of the grid (T/T/S/S skipped to cut noise). */
  showWeekdayLabels?: boolean;
  /** Cell edge length in px. Default 14 (was 12) — a touch more spacious than graph paper. */
  cellSize?: number;
  /** When set, ignores `year` and renders the last N calendar days ending today instead
   * of a full Jan 1 – Dec 31 grid. Used for the sparse-data "recent activity" zoom. */
  rangeDays?: number;
};

type Cell = {
  date: Date;
  key: string;
  /** Whether this cell falls inside the rendered range (year, or last-N-days). */
  visible: boolean;
  mark?: YearLedgerMark;
};

const MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAY_LABELS: Record<number, string> = { 1: "M", 3: "W", 5: "F" };

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
        visible: cursor.getUTCFullYear() === year,
        mark: byDate.get(key),
      });
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    weeks.push(week);
  }
  return weeks;
}

/** Last `days` calendar days ending today, padded out to full Sun–Sat weeks
 * (padding cells are not `visible`, matching the year grid's convention). */
function buildRangeWeeks(days: number, byDate: Map<string, YearLedgerMark>): Cell[][] {
  const today = new Date();
  const end = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()));
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - (days - 1));

  const gridStart = new Date(start);
  gridStart.setUTCDate(gridStart.getUTCDate() - gridStart.getUTCDay());
  const gridEnd = new Date(end);
  gridEnd.setUTCDate(gridEnd.getUTCDate() + (6 - gridEnd.getUTCDay()));

  const weeks: Cell[][] = [];
  const cursor = new Date(gridStart);
  while (cursor <= gridEnd) {
    const week: Cell[] = [];
    for (let d = 0; d < 7; d++) {
      const key = toKey(cursor);
      const visible = cursor >= start && cursor <= end;
      week.push({ date: new Date(cursor), key, visible, mark: byDate.get(key) });
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    weeks.push(week);
  }
  return weeks;
}

/** One label per week-column where a month starts (the week containing that
 * month's day-1), positioned above the first column touched by that month. */
function monthLabelsForWeeks(weeks: Cell[][]): { weekIndex: number; label: string }[] {
  const labels: { weekIndex: number; label: string }[] = [];
  weeks.forEach((week, wi) => {
    for (const cell of week) {
      if (!cell.visible) continue;
      if (cell.date.getUTCDate() === 1) {
        labels.push({ weekIndex: wi, label: MONTH_ABBR[cell.date.getUTCMonth()] });
      }
    }
  });
  return labels;
}

/**
 * Grid of calendar-day squares, one per day in the rendered range (a full
 * year, or the last N days via `rangeDays`). Empty (unmarked) squares are
 * transparent with a 1px --ground-3 outline only — R3: never rendered with
 * gain-soft/loss-soft, which would read as "flat" instead of "unmarked".
 * Colored squares scale saturation to |return|.
 */
export function YearLedger({
  year,
  marks,
  scaleMax = 0.03,
  showMonthLabels = false,
  showWeekdayLabels = false,
  cellSize = 14,
  rangeDays,
}: YearLedgerProps) {
  const [hover, setHover] = useState<{ cell: Cell; x: number; y: number } | null>(null);

  const byDate = new Map(marks.map((m) => [m.date, m]));
  const weeks = rangeDays ? buildRangeWeeks(rangeDays, byDate) : buildWeeks(year, byDate);
  const monthLabels = showMonthLabels ? monthLabelsForWeeks(weeks) : [];

  const cellStyle: CSSProperties = { width: cellSize, height: cellSize };
  const columnStyle: CSSProperties = { width: cellSize };
  // Month-row sits above the grid, not the weekday column, so it needs to be
  // nudged right by the weekday column's width + the layout gap to keep its
  // columns lined up with the grid's week columns.
  const monthRowStyle: CSSProperties = showWeekdayLabels
    ? { marginLeft: `calc(${cellSize}px + var(--space-2))` }
    : {};

  return (
    <div className="year-ledger">
      {showMonthLabels && (
        <div className="year-ledger__month-row" style={monthRowStyle}>
          {weeks.map((_week, wi) => {
            const label = monthLabels.find((m) => m.weekIndex === wi)?.label;
            return (
              <div key={wi} className="year-ledger__month-label" style={columnStyle}>
                {label ?? ""}
              </div>
            );
          })}
        </div>
      )}

      <div className="year-ledger__layout">
        {showWeekdayLabels && (
          <div className="year-ledger__weekday-col">
            {[0, 1, 2, 3, 4, 5, 6].map((dow) => (
              <div key={dow} className="year-ledger__weekday-label" style={cellStyle}>
                {WEEKDAY_LABELS[dow] ?? ""}
              </div>
            ))}
          </div>
        )}

        <div className="year-ledger__grid">
          {weeks.map((week, wi) => (
            <div key={wi} className="year-ledger__week">
              {week.map((cell) => {
                if (!cell.visible) {
                  return (
                    <div
                      key={cell.key}
                      className="year-ledger__cell year-ledger__cell--pad"
                      style={cellStyle}
                      aria-hidden="true"
                    />
                  );
                }

                const m = cell.mark;
                const hasReturn = m?.return_pct != null;
                const style: CSSProperties = { ...cellStyle };
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
