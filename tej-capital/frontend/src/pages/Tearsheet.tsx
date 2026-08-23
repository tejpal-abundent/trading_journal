import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { useMonthlyTearsheet, useEquitySeries } from "../hooks/useMetrics";
import { useCreateToken } from "../hooks/useAllocator";
import { MetricCard } from "../components/MetricCard";
import { VerdictBand } from "../components/VerdictBand";
import { MonthlyGrid, type MonthlyGridRow } from "../components/MonthlyGrid";
import { EmptyState } from "../components/EmptyState";
import { Button } from "../components/Button";
import { TextareaField } from "../components/TextField";
import { pct, num } from "../lib/format";
import { aggregateMonths } from "../lib/monthlyAgg";
import { buildFlatMetricTable } from "../lib/metricMeta";
import { api } from "../lib/api";

const COMMENTARY_TAG = "tearsheet-commentary";
const COMMENTARY_PLACEHOLDER =
  "What went wrong this month, and what are you changing? Write it as if to someone who has your money.";

type JournalEntry = { id: string; entry_date: string; body: string; tags: string[] };

export default function Tearsheet() {
  const { month: monthParam } = useParams<{ month: string }>();
  const [year, month] = (monthParam ?? "").split("-").map(Number);

  const { data, isLoading } = useMonthlyTearsheet(year, month);
  const { data: equity } = useEquitySeries();
  const createToken = useCreateToken();

  const [commentaryEntry, setCommentaryEntry] = useState<JournalEntry | null>(null);
  const [commentary, setCommentary] = useState("");
  const [saving, setSaving] = useState(false);
  const [pdfWarning, setPdfWarning] = useState<string | null>(null);
  const [linkCopied, setLinkCopied] = useState(false);

  useEffect(() => {
    if (!monthParam) return;
    api.get<JournalEntry[]>(`/journal?tag=${COMMENTARY_TAG}`).then((entries) => {
      const existing = entries.find((e) => e.entry_date.slice(0, 7) === monthParam) ?? null;
      setCommentaryEntry(existing);
      setCommentary(existing?.body ?? "");
    });
  }, [monthParam]);

  const monthPoints = useMemo(
    () => (equity ?? []).filter((p) => p.date.slice(0, 7) === monthParam),
    [equity, monthParam],
  );

  const yearGrid: MonthlyGridRow[] = useMemo(() => {
    if (!year) return [];
    const months = aggregateMonths(equity ?? []).filter((m) => m.year === year);
    const byMonth = new Map(months.map((m) => [m.month, m]));
    return [{ year, months: Array.from({ length: 12 }, (_, i) => ({ value: byMonth.get(i + 1)?.value ?? null })) }];
  }, [equity, year]);

  async function saveCommentary() {
    if (!monthParam || commentary.trim().length === 0) return;
    setSaving(true);
    try {
      if (commentaryEntry) {
        await api.patch(`/journal/${commentaryEntry.id}`, { body: commentary });
      } else {
        const created = await api.post<JournalEntry>("/journal", {
          entry_date: `${monthParam}-01`, body: commentary, tags: [COMMENTARY_TAG],
        });
        setCommentaryEntry(created);
      }
    } finally {
      setSaving(false);
    }
  }

  async function downloadPdf() {
    setPdfWarning(null);
    const res = await fetch(`/api/export/tearsheet/${year}/${month}.pdf`);
    const warning = res.headers.get("X-Tej-Warning");
    const contentType = res.headers.get("content-type") ?? "";
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    if (contentType.includes("html")) {
      window.open(url, "_blank");
      if (warning) setPdfWarning(warning);
    } else {
      const a = document.createElement("a");
      a.href = url;
      a.download = `tearsheet-${year}-${String(month).padStart(2, "0")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }

  async function copyAllocatorLink() {
    const expires = new Date();
    expires.setFullYear(expires.getFullYear() + 1);
    const token = await createToken.mutateAsync({ label: `Tearsheet ${monthParam}`, expires_at: expires.toISOString() });
    await navigator.clipboard.writeText(`${window.location.origin}/tej-capital/share/${token.token}`);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 3000);
  }

  if (!monthParam || Number.isNaN(year) || Number.isNaN(month)) {
    return <EmptyState title="Tearsheet" body="Pick a month from the Monthly Returns grid to open its tearsheet." cta={{ label: "Monthly Returns", to: "/monthly" }} />;
  }
  if (isLoading) {
    return <EmptyState title="Tearsheet" body={`Loading the tearsheet for ${monthParam}…`} />;
  }
  if (!data || data.verdict.n_days === 0) {
    return <EmptyState title="No data for this month" body="This month has no marked days yet." cta={{ label: "Monthly Returns", to: "/monthly" }} />;
  }

  const flatMetrics = buildFlatMetricTable(data.metric_groups);

  return (
    <div className="tearsheet">
      <div className="tearsheet__actions">
        <Button variant="secondary" onClick={downloadPdf}>Download PDF</Button>
        <Button variant="secondary" onClick={copyAllocatorLink} disabled={createToken.isPending}>
          {linkCopied ? "Link copied" : "Copy allocator link"}
        </Button>
      </div>

      {pdfWarning && <div className="banner banner--caution page-section">{pdfWarning}</div>}

      <div className="tearsheet__header">
        <div className="tearsheet__brand">T&amp;M CAPITAL</div>
        <div className="tearsheet__meta">
          <div>Discretionary multi-asset strategy</div>
          <div>{monthParam} · {data.source === "frozen" ? `frozen as of ${data.as_of_date}` : "live"}</div>
        </div>
      </div>

      <div className="metric-grid-4">
        <MetricCard label="Cumulative return" value={pct(data.headline.cumulative_twr.value)} n={data.headline.cumulative_twr.n} />
        <MetricCard label="CAGR" value={pct(data.headline.cagr.value)} n={data.headline.cagr.n} />
        <MetricCard label="Sharpe" value={num(data.headline.sharpe.value)} n={data.headline.sharpe.n} />
        <MetricCard label="Max drawdown" value={pct(data.headline.max_drawdown.value)} n={data.headline.max_drawdown.n} tone="loss" />
      </div>

      <VerdictBand v={data.verdict} />

      <div className="chart-card">
        <div className="chart-card__title">Equity curve — {monthParam}</div>
        {monthPoints.length < 2 ? (
          <p className="page-lede">Not enough marked days this month to draw a curve.</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={monthPoints}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--ground-3)" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--ink-3)" }} minTickGap={30} />
              <YAxis tick={{ fontSize: 11, fill: "var(--ink-3)" }} width={48} />
              <Tooltip />
              <Line type="monotone" dataKey="equity" stroke="var(--accent)" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="chart-card">
        <div className="chart-card__title">Year to date</div>
        <MonthlyGrid rows={yearGrid} />
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

      <div className="tearsheet__commentary">
        <TextareaField
          label="Manager commentary (required)"
          value={commentary}
          onChange={(e) => setCommentary(e.target.value)}
          placeholder={COMMENTARY_PLACEHOLDER}
          rows={5}
          required
        />
        <div className="form-actions">
          <Button onClick={saveCommentary} disabled={saving || commentary.trim().length === 0}>
            {saving ? "Saving…" : "Save commentary"}
          </Button>
        </div>
      </div>

      <div className="tearsheet__footer">
        <p>
          Methodology: returns are time-weighted, computed daily from broker-reported closing equity and
          reconciled cash flows. All figures are self-reported by the manager and have not been independently
          audited. Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
}
