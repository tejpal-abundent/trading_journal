import { useMemo } from "react";
import { useNav } from "./useNav";
import type { YearLedgerMark } from "../components/YearLedger";
import { shiftISODate, todayISO } from "../lib/format";

export type LedgerStats = {
  markedDays: number;
  greenDays: number;
  redDays: number;
  flatDays: number;
  daysWithoutMark: number;
  /** Longest run of consecutive *marks* (gaps skipped) with return > 0. */
  longestGreenRun: number;
  /** Longest run of consecutive *marks* (gaps skipped) with return < 0. */
  longestRedRun: number;
  /** Longest run of consecutive *calendar days* with a mark — the habit metric. */
  longestMarkedStreak: number;
};

function daysBetweenInclusive(startISO: string, endISO: string): number {
  const [sy, sm, sd] = startISO.split("-").map(Number);
  const [ey, em, ed] = endISO.split("-").map(Number);
  const start = Date.UTC(sy, sm - 1, sd);
  const end = Date.UTC(ey, em - 1, ed);
  return Math.round((end - start) / 86_400_000) + 1;
}

export function computeLedgerStats(marks: YearLedgerMark[], year: number): LedgerStats {
  let green = 0;
  let red = 0;
  let flat = 0;
  let curGreen = 0;
  let curRed = 0;
  let longestGreen = 0;
  let longestRed = 0;

  for (const m of marks) {
    if (m.return_pct == null) continue;
    if (m.return_pct > 0) {
      green += 1;
      curGreen += 1;
      curRed = 0;
      longestGreen = Math.max(longestGreen, curGreen);
    } else if (m.return_pct < 0) {
      red += 1;
      curRed += 1;
      curGreen = 0;
      longestRed = Math.max(longestRed, curRed);
    } else {
      flat += 1;
      curGreen = 0;
      curRed = 0;
    }
  }

  // Discipline streak — longest run of consecutive *calendar* days marked, no gaps.
  let longestMarked = 0;
  let curMarked = 0;
  let prevDate: string | null = null;
  for (const m of marks) {
    curMarked = prevDate != null && shiftISODate(prevDate, 1) === m.date ? curMarked + 1 : 1;
    longestMarked = Math.max(longestMarked, curMarked);
    prevDate = m.date;
  }

  const today = todayISO();
  const isCurrentYear = today.slice(0, 4) === String(year);
  const endISO = isCurrentYear ? today : `${year}-12-31`;
  const totalDays = daysBetweenInclusive(`${year}-01-01`, endISO);
  const markedDays = marks.length;
  const daysWithoutMark = Math.max(0, totalDays - markedDays);

  return {
    markedDays,
    greenDays: green,
    redDays: red,
    flatDays: flat,
    daysWithoutMark,
    longestGreenRun: longestGreen,
    longestRedRun: longestRed,
    longestMarkedStreak: longestMarked,
  };
}

/**
 * Full-year ledger data for one account: fetches from Jan 1 of the *prior*
 * year so the first mark of `year` still has a prior-day baseline for its
 * return, then trims the output back down to `year`.
 */
export function useLedgerYear(accountId: string | undefined, year: number) {
  const since = `${year - 1}-01-01`;
  const query = useNav(accountId, since);

  const marks: YearLedgerMark[] = useMemo(() => {
    const rows = query.data ?? [];
    const out: YearLedgerMark[] = [];
    let prevEquity: number | null = null;
    for (const row of rows) {
      const equity = Number(row.closing_equity);
      // The very first mark in the account's whole history has no prior
      // day to diff against. Treat it as flat (0%) rather than null so it
      // still renders as a marked square (YearLedger treats return_pct ==
      // null as "no mark at all") instead of vanishing as an empty day.
      const return_pct = prevEquity != null && prevEquity !== 0 ? (equity - prevEquity) / prevEquity : 0;
      const pnl = prevEquity != null ? equity - prevEquity : null;
      if (row.as_of_date.slice(0, 4) === String(year)) {
        out.push({ date: row.as_of_date, return_pct, pnl });
      }
      prevEquity = equity;
    }
    return out;
  }, [query.data, year]);

  const stats = useMemo(() => computeLedgerStats(marks, year), [marks, year]);

  return { ...query, marks, stats };
}

/** Dates within [start, end] (inclusive) that have no mark, given a set of marked dates. */
export function findMissedDays(markedDates: Set<string>, startISO: string, endISO: string): string[] {
  const missed: string[] = [];
  let cursor = startISO;
  while (cursor <= endISO) {
    if (!markedDates.has(cursor)) missed.push(cursor);
    cursor = shiftISODate(cursor, 1);
  }
  return missed;
}
