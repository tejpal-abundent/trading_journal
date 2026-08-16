import { useMemo } from "react";
import { useEquitySeries } from "../hooks/useMetrics";
import { aggregateMonths } from "../lib/monthlyAgg";
import { MonthlyGrid, type MonthlyGridRow } from "../components/MonthlyGrid";
import { EmptyState } from "../components/EmptyState";
import { SectionHeader } from "../components/SectionHeader";
import { pct } from "../lib/format";

export default function Monthly() {
  const { data: equity, isLoading } = useEquitySeries();
  const months = useMemo(() => aggregateMonths(equity), [equity]);

  const rows: MonthlyGridRow[] = useMemo(() => {
    if (months.length === 0) return [];
    const years = Array.from(new Set(months.map((m) => m.year))).sort((a, b) => a - b);
    const byKey = new Map(months.map((m) => [`${m.year}-${m.month}`, m]));
    return years.map((year) => ({
      year,
      months: Array.from({ length: 12 }, (_, i) => {
        const m = byKey.get(`${year}-${i + 1}`);
        return { value: m ? m.value : null, n: m?.n };
      }),
    }));
  }, [months]);

  const values = months.map((m) => m.value);
  const positive = values.filter((v) => v > 0).length;
  const best = values.length ? Math.max(...values) : null;
  const worst = values.length ? Math.min(...values) : null;
  const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
  const stdev = values.length > 1 && avg != null
    ? Math.sqrt(values.reduce((a, b) => a + (b - avg) ** 2, 0) / (values.length - 1))
    : null;

  if (isLoading) {
    return <EmptyState title="Monthly Returns" body="Loading monthly returns…" />;
  }
  if (months.length === 0) {
    return (
      <EmptyState
        title="No marks yet"
        body="Enter today's closing equity and your record begins. Monthly returns appear here once you have at least one full trading month."
        cta={{ label: "Go to Today", to: "/" }}
      />
    );
  }

  return (
    <div>
      <SectionHeader title="Monthly Returns" />
      <p className="page-lede">
        Months with no trading are left blank, never shown as 0%. Click any month to open its tearsheet.
      </p>
      <div className="page-section">
        <MonthlyGrid rows={rows} />
      </div>
      <p className="ledger-footer">
        {months.length} months with data · {values.length ? pct(positive / values.length) : "—"} positive · best{" "}
        {pct(best)} · worst {pct(worst)} · average {pct(avg)} · stdev {pct(stdev)}
      </p>
    </div>
  );
}
