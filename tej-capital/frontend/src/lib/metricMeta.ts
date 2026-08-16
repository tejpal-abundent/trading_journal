import { pct, num } from "./format";
import type { Metric } from "./api";
import type { Tearsheet } from "../hooks/useMetrics";
import type { MetricGroupItem } from "../components/MetricGroup";

type Fmt = "pct" | "num" | "days";

function fmt(kind: Fmt, v: number | null): string {
  if (v == null) return "—";
  if (kind === "pct") return pct(v);
  if (kind === "days") return `${Math.round(v)}d`;
  return num(v);
}

type Def = { key: string; label: string; explainer: string; kind: Fmt };

const RETURNS: Def[] = [
  { key: "cumulative_twr", label: "Cumulative return", explainer: "Total time-weighted return since inception.", kind: "pct" },
  { key: "cagr", label: "CAGR", explainer: "Compound annual growth rate implied by the record so far.", kind: "pct" },
  { key: "annualised_return", label: "Annualised return", explainer: "Average daily return, scaled to a year.", kind: "pct" },
  { key: "avg_daily_return", label: "Average daily return", explainer: "Mean return across all marked days.", kind: "pct" },
  { key: "pct_positive_days", label: "Positive days", explainer: "Share of marked days that closed up.", kind: "pct" },
  { key: "best_day", label: "Best day", explainer: "Largest single-day gain in the record.", kind: "pct" },
  { key: "worst_day", label: "Worst day", explainer: "Largest single-day loss in the record.", kind: "pct" },
];

const RISK: Def[] = [
  { key: "annualised_volatility", label: "Annualised volatility", explainer: "How much daily returns swing, scaled to a year.", kind: "pct" },
  { key: "downside_deviation", label: "Downside deviation", explainer: "Volatility counted only on down days.", kind: "pct" },
  { key: "max_drawdown", label: "Max drawdown", explainer: "Largest peak-to-trough decline in equity.", kind: "pct" },
  { key: "current_drawdown", label: "Current drawdown", explainer: "Distance below the most recent equity peak, right now.", kind: "pct" },
  { key: "longest_drawdown_days", label: "Longest drawdown", explainer: "Most days spent underwater in a single stretch.", kind: "days" },
  { key: "ulcer_index", label: "Ulcer index", explainer: "Depth and duration of drawdowns combined into one number.", kind: "num" },
  { key: "var_95", label: "VaR (95%)", explainer: "Worst expected daily loss, 95% of the time.", kind: "pct" },
  { key: "cvar_95", label: "CVaR (95%)", explainer: "Average loss on the worst 5% of days.", kind: "pct" },
  { key: "skewness", label: "Skewness", explainer: "Whether the return distribution leans toward big gains or big losses.", kind: "num" },
  { key: "excess_kurtosis", label: "Excess kurtosis", explainer: "How fat the tails are versus a normal distribution.", kind: "num" },
];

const RISK_ADJUSTED: Def[] = [
  { key: "sharpe", label: "Sharpe ratio", explainer: "Return earned per unit of volatility taken.", kind: "num" },
  { key: "sortino", label: "Sortino ratio", explainer: "Like Sharpe, but only penalises downside volatility.", kind: "num" },
  { key: "calmar", label: "Calmar ratio", explainer: "CAGR divided by max drawdown.", kind: "num" },
  { key: "sterling", label: "Sterling ratio", explainer: "Return relative to the average of the worst drawdowns.", kind: "num" },
  { key: "burke", label: "Burke ratio", explainer: "Return relative to the combined severity of drawdowns.", kind: "num" },
  { key: "omega", label: "Omega ratio", explainer: "Ratio of total gains to total losses above a zero threshold.", kind: "num" },
  { key: "gain_to_pain", label: "Gain-to-pain", explainer: "Sum of all returns divided by the sum of all losses.", kind: "num" },
  { key: "tail_ratio", label: "Tail ratio", explainer: "Size of the best days versus the worst days.", kind: "num" },
  { key: "ulcer_performance_index", label: "Ulcer performance index", explainer: "Return earned per unit of drawdown pain.", kind: "num" },
  { key: "recovery_factor", label: "Recovery factor", explainer: "Total return divided by the worst drawdown.", kind: "num" },
];

const STATISTICAL_VALIDITY: Def[] = [
  { key: "sharpe_t_stat", label: "Sharpe t-statistic", explainer: "How many standard errors the Sharpe ratio is from zero.", kind: "num" },
  { key: "psr_vs_zero", label: "Probabilistic Sharpe (vs 0)", explainer: "Probability the true Sharpe ratio is above zero.", kind: "pct" },
  { key: "psr_vs_benchmark", label: "Probabilistic Sharpe (vs benchmark)", explainer: "Probability the true Sharpe ratio beats the benchmark.", kind: "pct" },
  { key: "deflated_sharpe", label: "Deflated Sharpe ratio", explainer: "Sharpe ratio adjusted for how many variants were tested.", kind: "pct" },
];

const TRADES: Def[] = [
  { key: "expectancy_r", label: "Expectancy", explainer: "Average R gained or lost per trade.", kind: "num" },
  { key: "payoff_ratio", label: "Payoff ratio", explainer: "Average winning trade size versus average losing trade size.", kind: "num" },
  { key: "profit_factor", label: "Profit factor", explainer: "Gross profit divided by gross loss.", kind: "num" },
];

export function buildMetricGroup(defs: Def[], source: Record<string, unknown> | undefined): MetricGroupItem[] {
  return defs.map((d) => {
    const m = source?.[d.key] as Metric | undefined;
    return { key: d.key, label: d.label, explainer: d.explainer, value: fmt(d.kind, m?.value ?? null), n: m?.n ?? 0 };
  });
}

export function buildDisciplineGroup(trades: Tearsheet["trades"] | undefined): MetricGroupItem[] {
  const gap = trades?.compliance_gap;
  const streaks = trades?.streaks;
  const conc = trades?.top_3_concentration;
  const n = 0;
  return [
    {
      key: "compliant_expectancy", label: "Rule-compliant expectancy",
      explainer: "Average R on trades that followed the written rules.",
      value: gap?.compliant_expectancy != null ? num(gap.compliant_expectancy) : "—", n,
    },
    {
      key: "noncompliant_expectancy", label: "Rule-breaking expectancy",
      explainer: "Average R on trades that broke the written rules.",
      value: gap?.noncompliant_expectancy != null ? num(gap.noncompliant_expectancy) : "—", n,
    },
    {
      key: "gap_p_value", label: "Gap significance (p-value)",
      explainer: "How likely the compliant/non-compliant gap is due to chance.",
      value: gap?.p_value != null ? gap.p_value.toFixed(3) : "—", n,
    },
    {
      key: "longest_win_streak", label: "Longest win streak",
      explainer: "Most consecutive winning trades.",
      value: streaks?.longest_win_streak != null ? String(streaks.longest_win_streak) : "—", n,
    },
    {
      key: "longest_loss_streak", label: "Longest loss streak",
      explainer: "Most consecutive losing trades.",
      value: streaks?.longest_loss_streak != null ? String(streaks.longest_loss_streak) : "—", n,
    },
    {
      key: "top_3_concentration", label: "Top-3 trade concentration",
      explainer: "Share of total profit produced by the three best trades.",
      value: conc?.top_n_share != null ? pct(conc.top_n_share) : "—", n,
    },
  ];
}

export const METRIC_GROUP_DEFS = {
  Returns: RETURNS,
  Risk: RISK,
  "Risk-Adjusted": RISK_ADJUSTED,
  "Statistical Validity": STATISTICAL_VALIDITY,
  Trades: TRADES,
};

/** Flat, non-collapsible metric table for print/factsheet contexts
 * (Tearsheet, Allocator view) — same source metrics, laid out for a
 * one-page read rather than an on-screen collapsible group. */
export function buildFlatMetricTable(tearsheet: Tearsheet): MetricGroupItem[] {
  return [
    ...buildMetricGroup(RETURNS.slice(0, 4), tearsheet.returns),
    ...buildMetricGroup(RISK.slice(0, 4), tearsheet.risk),
    ...buildMetricGroup(RISK_ADJUSTED.slice(0, 4), tearsheet.risk_adjusted),
    ...buildMetricGroup(TRADES, tearsheet.trades),
  ];
}
