import { useMemo } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Metric } from "../lib/api";
import { useAccounts } from "./useAccounts";

export type MetricScope = "composite" | "per_account";

export type DrawdownEntry = {
  depth: number;
  duration_days: number;
  peak_date: string;
  trough_date: string;
  recovery_date: string | null;
};

export type Verdict = {
  headline: string;
  detail: string;
  level: "ok" | "caution" | "not_yet_meaningful";
  n_days: number;
  days_needed: number | null;
  years_remaining: number | null;
};

export type Tearsheet = {
  returns: {
    cumulative_twr: Metric; cagr: Metric; annualised_return: Metric; avg_daily_return: Metric;
    pct_positive_days: Metric; best_day: Metric; worst_day: Metric;
  };
  risk: {
    annualised_volatility: Metric; downside_deviation: Metric; max_drawdown: Metric; current_drawdown: Metric;
    longest_drawdown_days: Metric; ulcer_index: Metric; var_95: Metric; cvar_95: Metric;
    skewness: Metric; excess_kurtosis: Metric; top_5_drawdowns: DrawdownEntry[];
  };
  risk_adjusted: {
    sharpe: Metric; sortino: Metric; calmar: Metric; sterling: Metric; burke: Metric;
    omega: Metric; gain_to_pain: Metric; tail_ratio: Metric; ulcer_performance_index: Metric; recovery_factor: Metric;
  };
  statistical_validity: {
    sharpe_t_stat: Metric; psr_vs_zero: Metric; psr_vs_benchmark: Metric; deflated_sharpe: Metric;
    sharpe_ci: [number, number] | null;
  };
  trades: {
    expectancy_r: Metric; payoff_ratio: Metric; profit_factor: Metric;
    top_3_concentration: { top_n_share: number | null; top_n_ids: string[] };
    compliance_gap: { compliant_expectancy: number | null; noncompliant_expectancy: number | null; p_value: number | null };
    streaks: { longest_win_streak?: number; longest_loss_streak?: number };
    mae_mfe: { avg_mae_r_winners: number | null; avg_mfe_r_losers: number | null };
  };
  verdict: Verdict;
};

export function useLiveTearsheet(scope: MetricScope = "composite", accountId?: string) {
  const qs = new URLSearchParams({ scope });
  if (accountId) qs.set("account_id", accountId);
  return useQuery({
    queryKey: ["metrics-live", scope, accountId ?? null],
    queryFn: () => api.get<Tearsheet>(`/metrics/live?${qs.toString()}`),
  });
}

export type MetricSnapshot = {
  id: string; as_of_date: string; scope: MetricScope; account_id: string | null;
  metrics: Tearsheet; ledger_hash: string; computed_at: string;
};

export function useSnapshots(params?: { since?: string; scope?: MetricScope; accountId?: string }) {
  const qs = new URLSearchParams();
  if (params?.since) qs.set("since", params.since);
  if (params?.scope) qs.set("scope", params.scope);
  if (params?.accountId) qs.set("account_id", params.accountId);
  const q = qs.toString();
  return useQuery({
    queryKey: ["metric-snapshots", params?.since ?? null, params?.scope ?? null, params?.accountId ?? null],
    queryFn: () => api.get<MetricSnapshot[]>(`/metrics/snapshots${q ? `?${q}` : ""}`),
  });
}

export function useFreezeSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { as_of_date: string; scope?: MetricScope; account_id?: string }) =>
      api.post<MetricSnapshot>("/metrics/freeze", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["metric-snapshots"], exact: false }),
  });
}

export type MonthlyTearsheet = {
  year: number; month: number; source: "frozen" | "live"; as_of_date: string | null;
  headline: { cumulative_twr: Metric; cagr: Metric; sharpe: Metric; max_drawdown: Metric };
  metric_groups: Tearsheet;
  verdict: Verdict;
  monthly_grid: { date: string; return: number }[];
};

/** GET /api/tearsheet/monthly?year=&month= — backs both /monthly's per-month
 * drill-down and the printable /tearsheet/:month page. */
export function useMonthlyTearsheet(year: number, month: number) {
  return useQuery({
    queryKey: ["tearsheet-monthly", year, month],
    queryFn: () => api.get<MonthlyTearsheet>(`/tearsheet/monthly?year=${year}&month=${month}`),
    enabled: Number.isFinite(year) && Number.isFinite(month) && month >= 1 && month <= 12,
  });
}

// ---------------------------------------------------------------------
// Chart-only equity series. The backend never exposes a raw daily return
// series over HTTP (only aggregate metrics + one month at a time via
// /api/tearsheet/monthly), so Performance's equity curve / drawdown /
// rolling-Sharpe charts are built client-side from account nav + flow
// marks. This mirrors app/core/returns.py's beginning-of-day-weighted
// composite_twr with end_of_day flow timing (the API default) closely
// enough for charting; it is NOT used for any headline number — those
// always come from useLiveTearsheet / useMonthlyTearsheet.
// ---------------------------------------------------------------------

type NavRow = { as_of_date: string; closing_equity: string };
type FlowRow = { as_of_date: string; amount: string };

export type EquityPoint = { date: string; return: number; equity: number; drawdown: number };

function dailyTwr(navByDate: Map<string, number>, flowByDate: Map<string, number>): Map<string, number> {
  const dates = Array.from(navByDate.keys()).sort();
  const out = new Map<string, number>();
  for (let i = 1; i < dates.length; i++) {
    const prevD = dates[i - 1];
    const d = dates[i];
    const prev = navByDate.get(prevD)!;
    if (!prev) continue;
    const cur = navByDate.get(d)!;
    const flow = flowByDate.get(d) ?? 0;
    out.set(d, (cur - flow - prev) / prev);
  }
  return out;
}

export function useEquitySeries() {
  const { data: accounts, isLoading: accountsLoading } = useAccounts();
  const ids = useMemo(() => (accounts ?? []).filter((a) => a.in_composite).map((a) => a.id), [accounts]);

  const navQueries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["nav", id, null],
      queryFn: () => api.get<NavRow[]>(`/accounts/${id}/nav`),
    })),
  });
  const flowQueries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["flows", id, null],
      queryFn: () => api.get<FlowRow[]>(`/accounts/${id}/flows`),
    })),
  });

  const isLoading = accountsLoading || navQueries.some((q) => q.isLoading) || flowQueries.some((q) => q.isLoading);
  const navReady = ids.length > 0 && navQueries.every((q) => q.data !== undefined);

  const data: EquityPoint[] = useMemo(() => {
    if (!navReady) return [];

    const perAccountReturns: Map<string, number>[] = [];
    const perAccountWeights: Map<string, number>[] = [];

    ids.forEach((_id, i) => {
      const navRows = navQueries[i]?.data ?? [];
      const flowRows = flowQueries[i]?.data ?? [];
      const navByDate = new Map(navRows.map((r) => [r.as_of_date, Number(r.closing_equity)]));
      const flowByDate = new Map<string, number>();
      for (const f of flowRows) flowByDate.set(f.as_of_date, (flowByDate.get(f.as_of_date) ?? 0) + Number(f.amount));

      perAccountReturns.push(dailyTwr(navByDate, flowByDate));

      const sortedDates = Array.from(navByDate.keys()).sort();
      const weights = new Map<string, number>();
      for (let i2 = 1; i2 < sortedDates.length; i2++) {
        weights.set(sortedDates[i2], navByDate.get(sortedDates[i2 - 1])!);
      }
      perAccountWeights.push(weights);
    });

    const allDates = new Set<string>();
    perAccountReturns.forEach((r) => r.forEach((_v, d) => allDates.add(d)));
    const sortedDates = Array.from(allDates).sort();

    let equity = 1.0;
    let peak = 1.0;
    const points: EquityPoint[] = [];
    for (const d of sortedDates) {
      let num = 0;
      let denom = 0;
      perAccountReturns.forEach((r, i) => {
        const w = perAccountWeights[i].get(d);
        if (r.has(d) && w != null && w > 0) {
          num += w * r.get(d)!;
          denom += w;
        }
      });
      if (denom <= 0) continue;
      const ret = num / denom;
      equity *= 1 + ret;
      peak = Math.max(peak, equity);
      points.push({ date: d, return: ret, equity, drawdown: equity / peak - 1 });
    }
    return points;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navReady, ids.join(","), navQueries.map((q) => q.dataUpdatedAt).join(","), flowQueries.map((q) => q.dataUpdatedAt).join(",")]);

  return { data, isLoading };
}

/** Rolling N-day annualised Sharpe over the client-side equity series.
 * Chart-only — headline Sharpe always comes from the backend. */
export function rollingSharpe(points: EquityPoint[], window = 63, tradingDaysPerYear = 252) {
  const out: { date: string; sharpe: number | null }[] = [];
  for (let i = 0; i < points.length; i++) {
    if (i < window - 1) {
      out.push({ date: points[i].date, sharpe: null });
      continue;
    }
    const slice = points.slice(i - window + 1, i + 1).map((p) => p.return);
    const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
    const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / (slice.length - 1);
    const std = Math.sqrt(variance);
    out.push({ date: points[i].date, sharpe: std === 0 ? 0 : (mean / std) * Math.sqrt(tradingDaysPerYear) });
  }
  return out;
}

/** Filters an equity series to a period, re-based so the first point's
 * equity is 1.0 (so period-scoped return % is relative to the window). */
export function filterPeriod(points: EquityPoint[], startISO: string | null): EquityPoint[] {
  if (!startISO) return points;
  const slice = points.filter((p) => p.date >= startISO);
  if (slice.length === 0) return slice;
  const base = slice[0].equity / (1 + slice[0].return);
  let peak = base;
  return slice.map((p) => {
    const equity = p.equity / base;
    peak = Math.max(peak, equity);
    return { ...p, equity, drawdown: equity / peak - 1 };
  });
}
