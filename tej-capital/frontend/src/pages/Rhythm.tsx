import {
  ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
import { useRhythm, type WeeklyReturn } from "../hooks/useRhythm";
import { MetricCard } from "../components/MetricCard";
import { SectionHeader } from "../components/SectionHeader";
import { EmptyState } from "../components/EmptyState";
import { pct, formatDateLong } from "../lib/format";

function paceTone(value: number | null, target: number): "neutral" | "gain" | "loss" {
  if (value == null) return "neutral";
  if (value >= target) return "gain";
  if (value < 0) return "loss";
  return "neutral";
}

function GapChip({ gapPct }: { gapPct: number | null }) {
  if (gapPct == null) return null;
  const bps = Math.round(gapPct * 10000);
  const tone = bps > 0 ? "ok" : bps < 0 ? "breach" : "neutral";
  const sign = bps > 0 ? "+" : "";
  return <span className={`chip chip--${tone}`}>{sign}{bps} bps vs target</span>;
}

function monthName(iso: string): string {
  const [y, m] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString("en-US", { month: "long", timeZone: "UTC" });
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function RhythmTooltip({ active, payload }: { active?: boolean; payload?: { payload: WeeklyReturn }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rhythm-tooltip">
      <div className="rhythm-tooltip__date">{formatDateLong(d.week_start)}</div>
      <div className="rhythm-tooltip__value">{pct(d.return_pct)}</div>
      <div>{d.trading_days} trading day{d.trading_days === 1 ? "" : "s"}</div>
    </div>
  );
}

const NOT_ENOUGH_MARKS_BODY =
  "The Rhythm view lights up once you have a full week of daily marks.";

export default function Rhythm() {
  const { data, isLoading } = useRhythm();

  if (isLoading || !data) {
    return <EmptyState title="Rhythm" body="Loading pacing data…" />;
  }

  const { today, this_week: thisWeek, this_month: thisMonth, weekly_returns: weeklyReturns } = data;

  const noDataAtAll =
    today.return.n === 0 && thisWeek.return.n === 0 && thisMonth.return.n === 0 && weeklyReturns.length === 0;

  if (noDataAtAll) {
    return (
      <div>
        <SectionHeader title="Rhythm" />
        <p className="page-lede">Pacing against your daily, weekly, monthly targets.</p>
        <EmptyState title="Not enough marks yet" body={NOT_ENOUGH_MARKS_BODY} cta={{ label: "Go to Today", to: "/" }} />
      </div>
    );
  }

  const returnValues = weeklyReturns.map((w) => w.return_pct);
  const green = returnValues.filter((v) => v > 0).length;
  const red = returnValues.filter((v) => v < 0).length;

  return (
    <div>
      <SectionHeader title="Rhythm" />
      <p className="page-lede">Pacing against your daily, weekly, monthly targets.</p>

      <div className="metric-grid-3">
        <MetricCard
          label="Today"
          value={pct(today.return.value)}
          n={today.return.n}
          sub={`Target ${pct(today.target_pct)}`}
          tone={paceTone(today.return.value, today.target_pct)}
        />
        <MetricCard
          label="This week"
          value={pct(thisWeek.return.value)}
          n={thisWeek.return.n}
          sub={`Target ${pct(thisWeek.target_pct)} · ${thisWeek.trading_days_so_far}/5 days`}
          tone={paceTone(thisWeek.return.value, thisWeek.target_pct)}
          chip={<GapChip gapPct={thisWeek.gap_pct} />}
        />
        <MetricCard
          label="This month"
          value={pct(thisMonth.return.value)}
          n={thisMonth.return.n}
          sub={`Target ${pct(thisMonth.target_pct)} · ${monthName(thisMonth.month_start)} · ${thisMonth.trading_days_so_far} days elapsed`}
          tone={paceTone(thisMonth.return.value, thisMonth.target_pct)}
          chip={<GapChip gapPct={thisMonth.gap_pct} />}
        />
      </div>

      <div className="page-section">
        <div className="chart-card">
          <div className="chart-card__title">52-week returns</div>
          {weeklyReturns.length === 0 ? (
            <EmptyState title="Not enough marks yet" body={NOT_ENOUGH_MARKS_BODY} />
          ) : (
            <>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={weeklyReturns}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--ground-3)" />
                  <XAxis
                    dataKey="week_start"
                    tick={{ fontSize: 11, fill: "var(--ink-3)" }}
                    interval={3}
                    tickFormatter={(v: string) => formatDateLong(v)}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "var(--ink-3)" }}
                    tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                    width={48}
                  />
                  <ReferenceLine y={thisWeek.target_pct} stroke="var(--accent)" strokeDasharray="4 4" />
                  <Tooltip content={<RhythmTooltip />} />
                  <Bar dataKey="return_pct">
                    {weeklyReturns.map((d) => (
                      <Cell key={d.week_start} fill={d.return_pct >= 0 ? "var(--gain)" : "var(--loss)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="rhythm-footer">
                {weeklyReturns.length} weeks · {green} green · {red} red · median {pct(median(returnValues))} ·{" "}
                best {pct(Math.max(...returnValues))} · worst {pct(Math.min(...returnValues))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
