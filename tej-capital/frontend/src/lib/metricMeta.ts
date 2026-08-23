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
  { key: "cumulative_twr", label: "Cumulative return", explainer: "The percent your account grew, cleaned of deposits and withdrawals. +5% means $100 became $105 purely from trading.", kind: "pct" },
  { key: "cagr", label: "CAGR", explainer: "The steady yearly growth rate that would explain your track record. If you compounded at this rate every year, you'd end up where you are today.", kind: "pct" },
  { key: "annualised_return", label: "Annualised return", explainer: "Your average daily return, scaled up to a full year. Simpler than CAGR — no compounding assumption.", kind: "pct" },
  { key: "avg_daily_return", label: "Average daily return", explainer: "Your typical day. Doesn't tell you much on its own — pair with volatility to know if it's earned or lucky.", kind: "pct" },
  { key: "pct_positive_days", label: "Positive days", explainer: "Fraction of trading days that ended up. 50% is normal; 70%+ deserves a look at skewness (see Risk).", kind: "pct" },
  { key: "best_day", label: "Best day", explainer: "Your single biggest UP day, in percent.", kind: "pct" },
  { key: "worst_day", label: "Worst day", explainer: "Your single biggest DOWN day. If it's much bigger than the best day in absolute terms, you have a tail problem.", kind: "pct" },
];

const RISK: Def[] = [
  { key: "annualised_volatility", label: "Annualised volatility", explainer: "How wildly your daily returns swing, scaled to a year. 10–20% is normal; 40% is a rollercoaster.", kind: "pct" },
  { key: "downside_deviation", label: "Downside deviation", explainer: "Volatility but only counting DOWN moves. What Sortino uses under the hood.", kind: "pct" },
  { key: "max_drawdown", label: "Max drawdown", explainer: "The worst peak-to-bottom drop your account has ever had. −10% means at some point you were 10% below a previous high.", kind: "pct" },
  { key: "current_drawdown", label: "Current drawdown", explainer: "How far below your last peak you are RIGHT NOW. 0% means you're at all-time high.", kind: "pct" },
  { key: "longest_drawdown_days", label: "Longest drawdown", explainer: "The longest stretch you spent below a previous high. Time-under-water scares allocators as much as depth.", kind: "days" },
  { key: "ulcer_index", label: "Ulcer index", explainer: "One number that captures both depth AND length of drawdowns. Lower is smoother.", kind: "num" },
  { key: "var_95", label: "VaR (95%)", explainer: "On your worst 5% of trading days, expect losses at least this bad. Negative number.", kind: "pct" },
  { key: "cvar_95", label: "CVaR (95%)", explainer: "The AVERAGE loss on those worst 5% days. Always worse than VaR.", kind: "pct" },
  { key: "skewness", label: "Skewness", explainer: "Shape of your return curve. Negative = many small wins + occasional big loss (dangerous, SMC-scalper signature). Positive = the opposite (safer).", kind: "num" },
  { key: "excess_kurtosis", label: "Excess kurtosis", explainer: "How fat your tails are. Above 3 means outliers happen more than a normal bell curve would predict.", kind: "num" },
];

const RISK_ADJUSTED: Def[] = [
  { key: "sharpe", label: "Sharpe ratio", explainer: "Reward per unit of risk. Above 1 is good, above 2 is rare, above 3 is either genius or a small sample. Uses ALL volatility (up AND down).", kind: "num" },
  { key: "sortino", label: "Sortino ratio", explainer: "Like Sharpe but only counts DOWN volatility as risk. Kinder to strategies with big winning days.", kind: "num" },
  { key: "calmar", label: "Calmar ratio", explainer: "Yearly return divided by worst drawdown. Above 1 = you make back more than you lose in a bad stretch.", kind: "num" },
  { key: "sterling", label: "Sterling ratio", explainer: "Cousin of Calmar with a different drawdown formula. Usually similar in shape.", kind: "num" },
  { key: "burke", label: "Burke ratio", explainer: "Another Calmar cousin using sum-of-squared-drawdowns. Penalises multiple bad periods.", kind: "num" },
  { key: "omega", label: "Omega ratio", explainer: "Ratio of gains above zero to losses below zero. Above 1.5 is good. Better than Sharpe for non-normal returns.", kind: "num" },
  { key: "gain_to_pain", label: "Gain-to-pain", explainer: "Total gains divided by sum of losses. Intuitive: 2.0 means you make $2 for every $1 you lose.", kind: "num" },
  { key: "tail_ratio", label: "Tail ratio", explainer: "95th percentile return divided by 5th percentile loss. High = winners are much bigger than losers in the tails.", kind: "num" },
  { key: "ulcer_performance_index", label: "Ulcer performance index", explainer: "Excess return per unit of Ulcer Index. Rewards smooth curves, not just profitable ones.", kind: "num" },
  { key: "recovery_factor", label: "Recovery factor", explainer: "Cumulative return divided by max drawdown. How efficiently you claw back losses.", kind: "num" },
];

const STATISTICAL_VALIDITY: Def[] = [
  { key: "sharpe_t_stat", label: "Sharpe t-statistic", explainer: "Statistical confidence in your Sharpe. Above 2 = probably not luck at 95% confidence.", kind: "num" },
  { key: "psr_vs_zero", label: "Probabilistic Sharpe (vs 0)", explainer: "Probability your TRUE Sharpe is above zero, given your sample size. Above 95% = trustworthy.", kind: "pct" },
  { key: "psr_vs_benchmark", label: "Probabilistic Sharpe (vs benchmark)", explainer: "Same but versus the benchmark you set in Settings. Above 95% = you probably beat the benchmark.", kind: "pct" },
  { key: "deflated_sharpe", label: "Deflated Sharpe ratio", explainer: "Sharpe corrected for how many backtest variants you tested. Punishes cherry-picking.", kind: "pct" },
];

const TRADES: Def[] = [
  { key: "expectancy_r", label: "Expectancy", explainer: "Average R-multiple per trade. Above 0.15R is a real edge; below 0 means retire the setup.", kind: "num" },
  { key: "payoff_ratio", label: "Payoff ratio", explainer: "Average winner divided by average loser (in R). Above 1.5 is comfortable.", kind: "num" },
  { key: "profit_factor", label: "Profit factor", explainer: "Sum of wins divided by sum of losses. Above 1.5 = you make $1.50 for every $1 you lose.", kind: "num" },
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
      explainer: "Average R on trades where you followed the written rules. Should be positive; the gap vs the non-compliant number below is where your real edge lives.",
      value: gap?.compliant_expectancy != null ? num(gap.compliant_expectancy) : "—", n,
    },
    {
      key: "noncompliant_expectancy", label: "Rule-breaking expectancy",
      explainer: "Average R on trades where you broke your written rules. Usually negative. If it's less negative than you'd expect, that doesn't mean rule-breaking works — it means your sample is small.",
      value: gap?.noncompliant_expectancy != null ? num(gap.noncompliant_expectancy) : "—", n,
    },
    {
      key: "gap_p_value", label: "Gap significance (p-value)",
      explainer: "How likely the compliant vs non-compliant gap is pure luck. Below 0.05 = probably real; above 0.20 = might be noise.",
      value: gap?.p_value != null ? gap.p_value.toFixed(3) : "—", n,
    },
    {
      key: "longest_win_streak", label: "Longest win streak",
      explainer: "Most consecutive winning trades in a row.",
      value: streaks?.longest_win_streak != null ? String(streaks.longest_win_streak) : "—", n,
    },
    {
      key: "longest_loss_streak", label: "Longest loss streak",
      explainer: "Most consecutive losing trades in a row. If this is much bigger than any period of your rule-following would predict, revisit stop discipline.",
      value: streaks?.longest_loss_streak != null ? String(streaks.longest_loss_streak) : "—", n,
    },
    {
      key: "top_3_concentration", label: "Top-3 trade concentration",
      explainer: "Fraction of your profit that came from your three best trades. Above 50% = your effective sample is smaller than trade count suggests.",
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
