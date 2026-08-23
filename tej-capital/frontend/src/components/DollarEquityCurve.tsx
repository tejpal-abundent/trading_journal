import {
  ResponsiveContainer, ComposedChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
import { money } from "../lib/format";

export type DollarEquityPoint = { date: string; dollars: number };

export type DollarEquityCurveProps = {
  data: DollarEquityPoint[];
  /** Break-even reference line — the account's starting capital. */
  startingCapital: number;
  height?: number;
};

/** Compact axis tick: $15.5k, $1.2m, $850. */
function formatCompactDollar(v: number): string {
  const sign = v < 0 ? "-" : "";
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(1)}m`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(1)}k`;
  return `${sign}$${abs.toFixed(0)}`;
}

/**
 * Dollar-denominated equity curve, shown directly below the percentage
 * equity curve on Performance. Same underlying series, just re-expressed
 * in raw dollars so "am I making money" reads without mental compounding.
 */
export function DollarEquityCurve({ data, startingCapital, height = 240 }: DollarEquityCurveProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data}>
        <defs>
          <linearGradient id="dollar-equity-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.15} />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--ground-3)" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: "var(--ink-3)", fontFamily: "var(--font-mono)" }}
          minTickGap={40}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--ink-3)", fontFamily: "var(--font-mono)" }}
          tickFormatter={formatCompactDollar}
          width={56}
          domain={[
            (min: number) => Math.min(min, startingCapital) * 0.998,
            (max: number) => Math.max(max, startingCapital) * 1.002,
          ]}
        />
        <Tooltip
          formatter={(v: unknown) => money(Number(v))}
          labelStyle={{ color: "var(--ink-1)", fontFamily: "var(--font-mono)" }}
          contentStyle={{ fontFamily: "var(--font-mono)" }}
        />
        <ReferenceLine y={startingCapital} stroke="var(--ink-4)" strokeDasharray="4 4" />
        <Area
          type="monotone"
          dataKey="dollars"
          stroke="var(--accent)"
          strokeWidth={1.5}
          fill="url(#dollar-equity-fill)"
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
