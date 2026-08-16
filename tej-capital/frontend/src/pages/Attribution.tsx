import { useState } from "react";
import { useAttribution, useConcentration, useComplianceGap, type AttributionBy } from "../hooks/useAttribution";
import { SectionHeader } from "../components/SectionHeader";
import { SegmentedControl } from "../components/SegmentedControl";
import { EmptyState } from "../components/EmptyState";
import { pct, num } from "../lib/format";

const GROUPINGS: { value: AttributionBy; label: string }[] = [
  { value: "setup", label: "Setup" },
  { value: "asset", label: "Asset" },
  { value: "session", label: "Session" },
  { value: "htf", label: "HTF" },
  { value: "dow", label: "Day of week" },
];

export default function Attribution() {
  const [by, setBy] = useState<AttributionBy>("setup");
  const { data: rows, isLoading } = useAttribution(by);
  const concentration = useConcentration();
  const gap = useComplianceGap();

  return (
    <div>
      <SectionHeader
        title="Attribution"
        action={<SegmentedControl options={GROUPINGS} value={by} onChange={setBy} />}
      />

      {concentration.data && concentration.data.top_n_share != null && (
        <div className="banner banner--caution page-section">
          Three trades produced {pct(concentration.data.top_n_share, 0)} of your profit. Your effective sample size
          is much smaller than your trade count suggests.
        </div>
      )}

      {gap.data && gap.data.p_value != null && gap.data.p_value < 0.05 && (
        <div className="banner banner--info page-section">
          Trades where you followed your rules: {signed(gap.data.compliant_expectancy)}R average, {gap.counts.compliant}{" "}
          trades. Trades where you didn't: {signed(gap.data.noncompliant_expectancy)}R average, {gap.counts.noncompliant}{" "}
          trades. The gap is unlikely to be chance. Your problem isn't strategy.
        </div>
      )}
      {gap.data && gap.data.p_value != null && gap.data.p_value >= 0.05 && (
        <div className="banner banner--info page-section">
          Trades where you followed your rules: {signed(gap.data.compliant_expectancy)}R average, {gap.counts.compliant}{" "}
          trades. Trades where you didn't: {signed(gap.data.noncompliant_expectancy)}R average, {gap.counts.noncompliant}{" "}
          trades. That gap is not yet statistically distinguishable from chance (p={gap.data.p_value.toFixed(2)}).
        </div>
      )}

      {isLoading ? (
        <EmptyState title="Attribution" body="Loading attribution data…" />
      ) : !rows || rows.length === 0 ? (
        <EmptyState
          title="Not enough trades yet"
          body="Attribution breaks down performance once you have closed trades to group."
          cta={{ label: "Log a trade", to: "/trades/new" }}
        />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>{GROUPINGS.find((g) => g.value === by)?.label}</th>
              <th>Trades</th>
              <th>Win rate</th>
              <th>Avg win R</th>
              <th>Avg loss R</th>
              <th>Expectancy R</th>
              <th>Total R</th>
              <th>Profit factor</th>
              <th>Share of profit</th>
              <th>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.group} className={`row--${row.verdict}`}>
                <td>{row.group}</td>
                <td className="data-table__num">{row.trade_count}</td>
                <td className="data-table__num">{pct(row.win_rate)}</td>
                <td className="data-table__num">{num(row.avg_win_r)}</td>
                <td className="data-table__num">{num(row.avg_loss_r)}</td>
                <td className="data-table__num">{num(row.expectancy_r)}</td>
                <td className="data-table__num">{num(row.total_r)}</td>
                <td className="data-table__num">{num(row.profit_factor)}</td>
                <td className="data-table__num">{pct(row.share_of_total_profit)}</td>
                <td>{row.verdict.replace("_", " ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function signed(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}`;
}
