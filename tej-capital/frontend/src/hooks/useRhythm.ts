import { useQuery } from "@tanstack/react-query";
import { api, type Metric } from "../lib/api";

export type RhythmToday = {
  return: Metric;
  target_pct: number;
  trading_date: string;
};

export type RhythmWeek = {
  return: Metric;
  target_pct: number;
  week_start: string;
  trading_days_so_far: number;
  gap_pct: number | null;
};

export type RhythmMonth = {
  return: Metric;
  target_pct: number;
  month_start: string;
  trading_days_so_far: number;
  gap_pct: number | null;
};

export type WeeklyReturn = {
  week_start: string;
  return_pct: number;
  trading_days: number;
  iso_year: number;
  iso_week: number;
};

export type Rhythm = {
  today: RhythmToday;
  this_week: RhythmWeek;
  this_month: RhythmMonth;
  weekly_returns: WeeklyReturn[];
};

/** GET /api/rhythm — daily/weekly/monthly pacing against configurable
 * targets, backing the Rhythm page's pace strip + 52-week bar chart. */
export function useRhythm() {
  return useQuery({ queryKey: ["rhythm"], queryFn: () => api.get<Rhythm>("/rhythm") });
}
