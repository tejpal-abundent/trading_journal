import { useMemo, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";
import { useLiveTearsheet, useEquitySeries, rollingSharpe, filterPeriod } from "../hooks/useMetrics";
import { MetricCard } from "../components/MetricCard";
import { VerdictBand } from "../components/VerdictBand";
import { MetricGroup } from "../components/MetricGroup";
import { EmptyState } from "../components/EmptyState";
import { SectionHeader } from "../components/SectionHeader";
import { SegmentedControl } from "../components/SegmentedControl";
import { pct, num } from "../lib/format";
import { buildMetricGroup, buildDisciplineGroup, METRIC_GROUP_DEFS } from "../lib/metricMeta";

type Period = "inception" | "12m" | "ytd" | "custom";

function periodStart(period: Period, custom: string): string | null {
  const today = new Date();
  if (period === "inception") return null;
  if (period === "ytd") return `${today.getFullYear()}-01-01`;
  if (period === "12m") {
    const d = new Date(today);
    d.setFullYear(d.getFullYear() - 1);
    return d.toISOString().slice(0, 10);
  }
  return custom || null;
}

export default function Performance() {
  const { data: tearsheet, isLoading } = useLiveTearsheet("composite");
  const { data: equity, isLoading: equityLoading } = useEquitySeries();
  const [period, setPeriod] = useState<Period>("inception");
  const [customDate, setCustomDate] = useState("");

  const start = periodStart(period, customDate);
  const chartData = useMemo(() => filterPeriod(equity, start), [equity, start]);
  const sharpeSeries = useMemo(() => rollingSharpe(chartData, 63), [chartData]);

  if (isLoading) {
    return <EmptyState title="Performance" body="Loading the live tearsheet…" />;
  }
  if (!tearsheet || tearsheet.verdict.n_days === 0) {
    return (
      <EmptyState
        title="No marks yet"
        body="Enter today's closing equity and your record begins."
        cta={{ label: "Go to Today", to: "/" }}
      />
    );
  }

  const r = tearsheet.returns;
  const risk = tearsheet.risk;

  return (
    <div>
      <SectionHeader
        title="Performance"
        action={
          <SegmentedControl
            options={[
              { value: "inception", label: "Since inception" },
              { value: "12m", label: "Last 12 months" },
              { value: "ytd", label: "YTD" },
              { value: "custom", label: "Custom" },
            ]}
            value={period}
            onChange={setPeriod}
          />
        }
      />
      {period === "custom" && (
        <div className="page-section" style={{ maxWidth: 220 }}>
          <input
            type="date"
            className="field__input"
            aria-label="Custom period start"
            value={customDate}
            onChange={(e) => setCustomDate(e.target.value)}
          />
        </div>
      )}

      <div className="metric-grid-4">
        <MetricCard label="Cumulative return" value={pct(r.cumulative_twr.value)} n={r.cumulative_twr.n} tone={ton(r.cumulative_twr.value)} />
        <MetricCard label="Sharpe" value={num(tearsheet.risk_adjusted.sharpe.value)} n={tearsheet.risk_adjusted.sharpe.n} />
        <MetricCard label="Max drawdown" value={pct(risk.max_drawdown.value)} n={risk.max_drawdown.n} tone="loss" />
        <MetricCard label="Current drawdown" value={pct(risk.current_drawdown.value)} n={risk.current_drawdown.n} tone={risk.current_drawdown.value && risk.current_drawdown.value < 0 ? "loss" : "neutral"} />
      </div>

      <VerdictBand v={tearsheet.verdict} />

      <div className="page-section">
        <div className="chart-card">
          <div className="chart-card__title">Equity curve{start ? ` — from ${start}` : ""}</div>
          {equityLoading ? (
            <p className="page-lede">Loading equity series…</p>
          ) : chartData.length < 2 ? (
            <p className="page-lede">Not enough marked days in this period to draw a curve.</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--ground-3)" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--ink-3)" }} minTickGap={40} />
                <YAxis
                  tick={{ fontSize: 11, fill: "var(--ink-3)" }}
                  tickFormatter={(v) => `${((v - 1) * 100).toFixed(0)}%`}
                  width={48}
                  domain={["dataMin", "dataMax"]}
                />
                <Tooltip formatter={(v: unknown) => `${((Number(v) - 1) * 100).toFixed(2)}%`} labelStyle={{ color: "var(--ink-1)" }} />
                <Line type="monotone" dataKey="equity" stroke="var(--accent)" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="chart-card">
          <div className="chart-card__title">Drawdown</div>
          {chartData.length < 2 ? (
            <p className="page-lede">Not enough marked days in this period.</p>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--ground-3)" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--ink-3)" }} minTickGap={40} />
                <YAxis tick={{ fontSize: 11, fill: "var(--ink-3)" }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} width={48} />
                <Tooltip formatter={(v: unknown) => `${(Number(v) * 100).toFixed(2)}%`} />
                <Area type="monotone" dataKey="drawdown" stroke="var(--loss)" fill="var(--loss-soft)" strokeWidth={1.5} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="chart-card">
          <div className="chart-card__title">Five worst drawdowns</div>
          {risk.top_5_drawdowns.length === 0 ? (
            <p className="page-lede">No completed drawdowns yet.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr><th>Depth</th><th>Duration</th><th>Recovery</th></tr>
              </thead>
              <tbody>
                {risk.top_5_drawdowns.map((d) => (
                  <tr key={d.trough_date}>
                    <td className="data-table__num">{pct(d.depth)}</td>
                    <td className="data-table__num">{d.duration_days}d</td>
                    <td className="data-table__num">{d.recovery_date ?? "ongoing"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="chart-card">
          <div className="chart-card__title">Rolling 63-day Sharpe</div>
          {sharpeSeries.filter((s) => s.sharpe != null).length < 2 ? (
            <p className="page-lede">Need at least 63 marked days for a rolling window.</p>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={sharpeSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--ground-3)" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--ink-3)" }} minTickGap={40} />
                <YAxis tick={{ fontSize: 11, fill: "var(--ink-3)" }} width={40} />
                <Tooltip formatter={(v: unknown) => Number(v).toFixed(2)} />
                <Line type="monotone" dataKey="sharpe" stroke="var(--accent)" strokeWidth={1.5} dot={false} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="page-section">
        <MetricGroup title="Returns" items={buildMetricGroup(METRIC_GROUP_DEFS.Returns, r)} defaultOpen />
        <MetricGroup title="Risk" items={buildMetricGroup(METRIC_GROUP_DEFS.Risk, risk)} />
        <MetricGroup title="Risk-Adjusted" items={buildMetricGroup(METRIC_GROUP_DEFS["Risk-Adjusted"], tearsheet.risk_adjusted)} />
        <MetricGroup title="Statistical Validity" items={buildMetricGroup(METRIC_GROUP_DEFS["Statistical Validity"], tearsheet.statistical_validity)} />
        <MetricGroup title="Trades" items={buildMetricGroup(METRIC_GROUP_DEFS.Trades, tearsheet.trades)} />
        <MetricGroup title="Discipline" items={buildDisciplineGroup(tearsheet.trades)} />
      </div>
    </div>
  );
}

function ton(v: number | null): "neutral" | "gain" | "loss" {
  if (v == null) return "neutral";
  return v > 0 ? "gain" : v < 0 ? "loss" : "neutral";
}
