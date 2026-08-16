import type { ReactNode } from "react";
import { useParams } from "react-router-dom";
import { useAllocatorView } from "../hooks/useAllocator";
import { MetricCard } from "../components/MetricCard";
import { VerdictBand } from "../components/VerdictBand";
import { pct, num } from "../lib/format";
import { buildFlatMetricTable } from "../lib/metricMeta";
import type { Tearsheet } from "../hooks/useMetrics";
import "../design/components.css";

/**
 * Public, read-only shareable tearsheet. Deliberately outside <Layout> —
 * no side nav, no auth. The API (`GET /api/allocator/view`) already
 * redacts journal, emotional state, per-trade notes, and account balances;
 * this page simply never reaches for keys the payload doesn't contain.
 */
export default function Allocator() {
  const { token } = useParams<{ token: string }>();
  const { data, isLoading, isError } = useAllocatorView(token);

  if (isLoading) {
    return <AllocatorShell><p className="page-lede">Loading…</p></AllocatorShell>;
  }
  if (isError || !data) {
    return (
      <AllocatorShell>
        <div className="empty-state">
          <div className="empty-state__title">Link unavailable</div>
          <p className="empty-state__body">This allocator link is missing, expired, or has been revoked.</p>
        </div>
      </AllocatorShell>
    );
  }

  const flatMetrics = buildFlatMetricTable(data as unknown as Tearsheet);

  return (
    <AllocatorShell>
      <div className="tearsheet">
        <div className="tearsheet__header">
          <div className="tearsheet__brand">TEJ CAPITAL</div>
          <div className="tearsheet__meta">
            <div>{data.label}</div>
            <div>Generated {new Date(data.generated_at).toLocaleDateString()}</div>
          </div>
        </div>

        <div className="metric-grid-4">
          <MetricCard label="Cumulative return" value={pct(data.returns.cumulative_twr.value)} n={data.returns.cumulative_twr.n} />
          <MetricCard label="Sharpe" value={num(data.risk_adjusted.sharpe.value)} n={data.risk_adjusted.sharpe.n} />
          <MetricCard label="Max drawdown" value={pct(data.risk.max_drawdown.value)} n={data.risk.max_drawdown.n} tone="loss" />
          <MetricCard label="Current drawdown" value={pct(data.risk.current_drawdown.value)} n={data.risk.current_drawdown.n} />
        </div>

        <VerdictBand v={data.verdict} />

        <div className="chart-card">
          <div className="chart-card__title">Five worst drawdowns</div>
          <table className="data-table">
            <thead><tr><th>Depth</th><th>Duration</th><th>Recovery</th></tr></thead>
            <tbody>
              {data.risk.top_5_drawdowns.map((d) => (
                <tr key={d.trough_date}>
                  <td className="data-table__num">{pct(d.depth)}</td>
                  <td className="data-table__num">{d.duration_days}d</td>
                  <td className="data-table__num">{d.recovery_date ?? "ongoing"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="chart-card">
          <div className="chart-card__title">Metrics</div>
          <table className="data-table">
            <tbody>
              {flatMetrics.map((m) => (
                <tr key={m.key}><td>{m.label}</td><td className="data-table__num">{m.value}</td><td className="data-table__num">N={m.n}</td></tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="tearsheet__footer">
          <p>
            Methodology: returns are time-weighted, computed daily from broker-reported closing equity and
            reconciled cash flows. All figures are self-reported by the manager and have not been independently
            audited. Past performance does not guarantee future results.
          </p>
        </div>
      </div>
    </AllocatorShell>
  );
}

function AllocatorShell({ children }: { children: ReactNode }) {
  return (
    <div className="allocator-shell">
      <div className="allocator-shell__inner">{children}</div>
    </div>
  );
}
