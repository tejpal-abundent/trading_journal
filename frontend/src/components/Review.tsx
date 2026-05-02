import { useEffect, useState } from "react";
import { api, AnalyticsData, Review as ReviewT } from "../api";
import { labelize } from "../constants/tags";
import SampleIntegrityCard from "./SampleIntegrityCard";
import VarianceExpectationsCard from "./VarianceExpectationsCard";
import ProcessScorecardCard from "./ProcessScorecardCard";
import DontBailBanner from "./DontBailBanner";
import { confidenceBadgeClass } from "../lib/confidence";

const PRESETS = [
  { id: "7",   label: "7 days",  days: 7 },
  { id: "14",  label: "14 days", days: 14 },
  { id: "30",  label: "30 days", days: 30 },
  { id: "90",  label: "90 days", days: 90 },
] as const;

type PresetId = typeof PRESETS[number]["id"] | "custom";

export default function Review() {
  const [preset, setPreset] = useState<PresetId>("14");
  const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [reviews, setReviews] = useState<ReviewT[]>([]);
  const [showWrite, setShowWrite] = useState(false);
  const [reviewBody, setReviewBody] = useState("");
  const [savingReview, setSavingReview] = useState(false);
  const [activeReview, setActiveReview] = useState<ReviewT | null>(null);
  const [selectedConfluences, setSelectedConfluences] = useState<string[]>([]);
  const [allConfluences, setAllConfluences] = useState<string[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      let d: AnalyticsData;
      const filter = selectedConfluences.length ? { confluences: selectedConfluences } : {};
      if (preset === "custom" && from && to) {
        d = await api.getAnalytics({ from, to, ...filter });
      } else if (preset !== "custom") {
        const days = PRESETS.find(p => p.id === preset)?.days || 14;
        d = await api.getAnalytics({ days, ...filter });
      } else {
        return;
      }
      setData(d);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [preset, from, to, selectedConfluences]);
  useEffect(() => { api.listReviews().then(setReviews); }, []);
  useEffect(() => {
    api.listTrades().then(trades => {
      const counts = new Map<string, number>();
      trades.forEach(t => (t.confluences || []).forEach(c => counts.set(c, (counts.get(c) || 0) + 1)));
      const sorted = Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).map(([c]) => c);
      setAllConfluences(sorted);
    }).catch(() => {});
  }, []);

  const toggleConfluence = (c: string) =>
    setSelectedConfluences(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]);

  const saveReview = async () => {
    if (!data || !reviewBody.trim() || savingReview) return;
    setSavingReview(true);
    try {
      const r = await api.createReview({
        period_type: preset === "custom" ? "custom" : preset === "30" ? "month" : "week",
        period_start: data.period_start || "",
        period_end: data.period_end || "",
        notes: reviewBody,
      });
      setReviews(prev => [r, ...prev]);
      setReviewBody(""); setShowWrite(false);
    } finally {
      setSavingReview(false);
    }
  };

  const view = activeReview?.stats_snapshot || data;

  return (
    <div>
      <div className="flex gap-2 wrap mb-3 center">
        {PRESETS.map(p => (
          <button key={p.id}
            className={`btn btn-sm ${preset === p.id ? "btn-primary" : "btn-ghost"}`}
            onClick={() => { setPreset(p.id); setActiveReview(null); }}>
            {p.label}
          </button>
        ))}
        <button className={`btn btn-sm ${preset === "custom" ? "btn-primary" : "btn-ghost"}`}
          onClick={() => { setPreset("custom"); setActiveReview(null); }}>
          Custom
        </button>
        {preset === "custom" && (
          <>
            <input type="date" value={from} onChange={e => setFrom(e.target.value)} />
            <input type="date" value={to}   onChange={e => setTo(e.target.value)} />
          </>
        )}
      </div>

      {allConfluences.length > 0 && (
        <div className="card mb-3" style={{ padding: "10px 12px" }}>
          <div className="text-xs text-2 mb-1">
            Filter by confluences (intersection — trades with <b>all</b> selected tags)
          </div>
          <div className="chip-row">
            {allConfluences.map(c => (
              <span key={c}
                className={`chip ${selectedConfluences.includes(c) ? "selected" : ""}`}
                onClick={() => toggleConfluence(c)}>
                {c.replace(/_/g, " ")}
              </span>
            ))}
            {selectedConfluences.length > 0 && (
              <span className="chip" style={{ color: "var(--red)" }}
                onClick={() => setSelectedConfluences([])}>clear</span>
            )}
          </div>
        </div>
      )}

      {activeReview && (
        <div className="card" style={{ background: "var(--blue-bg)" }}>
          <div className="flex between center">
            <b>Viewing saved review: {activeReview.period_start?.slice(0,10)} → {activeReview.period_end?.slice(0,10)}</b>
            <button className="btn btn-sm btn-ghost" onClick={() => setActiveReview(null)}>Close</button>
          </div>
          <div className="text-sm mt-2" style={{ whiteSpace: "pre-wrap" }}>{activeReview.notes}</div>
        </div>
      )}

      {loading && !view && <p className="text-2 text-sm">Loading...</p>}
      {view && <Stats d={view} />}

      <div className="status-group">
        <h3>Saved reviews</h3>
        {reviews.length === 0 ? (
          <p className="text-2 text-xs">None yet.</p>
        ) : reviews.map(r => (
          <div key={r.id} className="card flex between center" style={{ padding: "8px 12px", cursor: "pointer" }}
            onClick={async () => setActiveReview(await api.getReview(r.id))}>
            <div>
              <b>{r.period_start?.slice(0,10)} → {r.period_end?.slice(0,10)}</b>
              <div className="text-xs text-2">{r.notes.slice(0, 80)}{r.notes.length > 80 ? "..." : ""}</div>
            </div>
            <button className="btn btn-sm btn-ghost" style={{ color: "var(--red)" }}
              onClick={async (e) => { e.stopPropagation(); if (confirm("Delete review?")) {
                await api.deleteReview(r.id);
                setReviews(prev => prev.filter(x => x.id !== r.id));
              }}}>Delete</button>
          </div>
        ))}
      </div>

      {!activeReview && !showWrite && (
        <button className="btn btn-primary mt-3" onClick={() => setShowWrite(true)} style={{ width: "100%" }}>
          + Write review for this period
        </button>
      )}
      {showWrite && (
        <div className="card mt-3">
          <textarea rows={5} placeholder="Reflection on this period..."
            value={reviewBody} onChange={e => setReviewBody(e.target.value)} />
          <div className="flex gap-2 mt-2" style={{ justifyContent: "flex-end" }}>
            <button className="btn btn-sm btn-ghost" onClick={() => setShowWrite(false)}>Cancel</button>
            <button className="btn btn-sm btn-primary" onClick={saveReview} disabled={savingReview}>
              {savingReview ? "Saving..." : "Save review"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Stats({ d }: { d: AnalyticsData }) {
  return (
    <div className="flex col gap-3">
      <DontBailBanner data={d.streak_expectations} />
      <div className="card">
        <div className="flex between center">
          <span><b>{d.total_trades}</b> trades · <b>{d.closed_trades}</b> closed · <b>{d.skipped_trades}</b> skipped</span>
          <span><b style={{ color: d.total_pnl >= 0 ? "var(--green)" : "var(--red)" }}>${d.total_pnl}</b></span>
        </div>
        <div className="kpis text-sm text-2 mt-1">
          Win rate <b>{d.win_rate}%</b>
          {d.win_rate_ci && (
            <span className={`badge ${confidenceBadgeClass(d.confidence)}`} style={{ marginLeft: 6 }}>
              n={d.n ?? d.closed_trades}, {d.confidence ?? ''}
            </span>
          )}
          {' · '}Avg score {d.avg_score} · Avg R {d.avg_rr}
        </div>
      </div>

      <div className="cards-grid" style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 12, marginTop: 12,
      }}>
        <SampleIntegrityCard data={d.sample_integrity} />
        <VarianceExpectationsCard data={d.streak_expectations} />
        <ProcessScorecardCard data={d.process_score} />
      </div>

      {d.edge_composite && (
        <div className="card" style={{ borderColor: "var(--green)", borderWidth: 2 }}>
          <div className="text-xs text-2">YOUR EDGE</div>
          <div className="font-500">{d.edge_composite.headline}</div>
          {d.edge_composite.count > 0 && (
            <div className="text-sm mt-1">
              {d.edge_composite.count} trades · {d.edge_composite.win_rate}% win rate
              {d.edge_composite.avg_rr != null && ` · ${d.edge_composite.avg_rr} avg R`}
              {d.edge_composite.total_pnl != null && ` · $${d.edge_composite.total_pnl} total P/L`}
            </div>
          )}
        </div>
      )}

      <div className="card">
        <h4 className="text-sm mb-2">Plan adherence</h4>
        <div className="text-sm">
          Rules followed {d.plan_adherence.rules_followed_pct}% of the time<br/>
          Win rate when followed: <b>{d.plan_adherence.rules_followed_win_rate}%</b><br/>
          Win rate when broken: <b>{d.plan_adherence.rules_broken_win_rate}%</b><br/>
          Skip rate: {d.plan_adherence.skip_rate}% · Retroactive: {d.plan_adherence.retroactive_rate}%
        </div>
      </div>

      <div className="card">
        <h4 className="text-sm mb-2">Risk discipline</h4>
        <div className="text-sm">
          Avg risk {d.risk_discipline.avg_risk_pct}% · Max {d.risk_discipline.max_risk_pct}%
          {d.risk_discipline.over_threshold_count > 0 && (
            <span style={{ color: "var(--red)" }}> · {d.risk_discipline.over_threshold_count} over threshold</span>
          )}
        </div>
        <div className="text-xs text-2 mt-1">
          {d.risk_discipline.histogram.map(b => (
            <span key={b.bucket} style={{ marginRight: 12 }}>
              {b.bucket}: {b.count}
            </span>
          ))}
        </div>
      </div>

      {d.confluence_impact && d.confluence_impact.length > 0 && (
        <div className="card">
          <h4 className="text-sm mb-2">Confluence impact</h4>
          <div className="text-xs text-2 mb-2">
            Win rate / P/L when each confluence was tagged on the plan. Use this to find the time-of-day, structure, or context combos that work for you.
          </div>
          <table className="text-sm" style={{ width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Confluence</th><th>Count</th><th>Win %</th><th>Total P/L</th>
              </tr>
            </thead>
            <tbody>
              {d.confluence_impact.map(r => (
                <tr key={r.tag}>
                  <td>{r.tag.replace(/_/g, " ")}</td>
                  <td align="center">{r.count}</td>
                  <td align="center">{r.win_rate}%</td>
                  <td align="right" style={{ color: r.total_pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                    ${r.total_pnl}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {d.mfe_mae_analysis && d.mfe_mae_analysis.count > 0 && (
        <div className="card">
          <h4 className="text-sm mb-2">MFE / MAE analysis</h4>
          <div className="text-xs text-2 mb-2">
            <b>Avg MFE on winners</b> tells you if you're cutting winners early. <b>Avg MAE on winners</b> tells you if your entries could be tighter.
          </div>
          <div className="text-sm" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
            {d.mfe_mae_analysis.avg_mfe_winners != null && (
              <div>Avg MFE (winners): <b>{d.mfe_mae_analysis.avg_mfe_winners}R</b></div>
            )}
            {d.mfe_mae_analysis.avg_mae_winners != null && (
              <div>Avg MAE (winners): <b>{d.mfe_mae_analysis.avg_mae_winners}R</b></div>
            )}
            {d.mfe_mae_analysis.avg_mfe_losers != null && (
              <div>Avg MFE (losers): <b>{d.mfe_mae_analysis.avg_mfe_losers}R</b></div>
            )}
            {d.mfe_mae_analysis.avg_mae_losers != null && (
              <div>Avg MAE (losers): <b>{d.mfe_mae_analysis.avg_mae_losers}R</b></div>
            )}
            {d.mfe_mae_analysis.max_mfe_all != null && (
              <div>Best MFE seen: <b>{d.mfe_mae_analysis.max_mfe_all}R</b></div>
            )}
          </div>
        </div>
      )}

      {d.mistake_impact.length > 0 && (
        <div className="card">
          <h4 className="text-sm mb-2">Mistake impact</h4>
          <table className="text-sm" style={{ width: "100%" }}>
            <thead>
              <tr><th align="left">Tag</th><th>Count</th><th>Win %</th><th>Total P/L</th></tr>
            </thead>
            <tbody>
              {d.mistake_impact.map(r => (
                <tr key={r.tag}>
                  <td>{r.tag === "(none)" ? <i>No mistakes</i> : labelize(r.tag)}</td>
                  <td align="center">{r.count}</td>
                  <td align="center">{r.win_rate}%</td>
                  <td align="right" style={{ color: r.total_pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                    ${r.total_pnl}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(d.emotion_impact.entry.length > 0 || d.emotion_impact.exit.length > 0) && (
        <div className="card">
          <h4 className="text-sm mb-2">Emotion impact</h4>
          <EmotionTable label="Entry" rows={d.emotion_impact.entry} />
          <EmotionTable label="Exit" rows={d.emotion_impact.exit} />
        </div>
      )}

      <div className="card">
        <h4 className="text-sm mb-2">Timing</h4>
        {Object.entries(d.timing_impact).map(([k, v]) => (
          <span key={k} style={{ marginRight: 16 }} className="text-sm">
            {labelize(k)}: <b>{v.count}</b> ({v.win_rate}% win)
          </span>
        ))}
      </div>

      {d.strategy_breakdown.length > 1 && (
        <div className="card">
          <h4 className="text-sm mb-2">Strategy breakdown</h4>
          {d.strategy_breakdown.map(s => (
            <div key={s.strategy} className="text-sm">
              <b>{s.strategy}</b>: {s.count} trades · {s.win_rate}% win · expectancy ${s.expectancy}
              {s.frequency_warning && (
                <span style={{ color: 'var(--yellow)', marginLeft: 8 }}>{s.frequency_warning}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {d.regime_coverage && (
        <div className="muted small" style={{ marginTop: 16, fontStyle: 'italic' }}>
          {d.regime_coverage.warning && <p>⚠ {d.regime_coverage.warning}</p>}
          <p>{d.regime_coverage.fat_tail_caveat}</p>
        </div>
      )}
    </div>
  );
}

function EmotionTable({ label, rows }: { label: string;
  rows: { tag: string; count: number; win_rate: number; avg_pnl: number; total_pnl: number }[] }) {
  if (!rows.length) return null;
  return (
    <div className="mt-2">
      <div className="text-xs text-2">{label}</div>
      {rows.slice(0, 5).map(r => (
        <div key={r.tag} className="text-sm flex between" style={{ paddingTop: 2 }}>
          <span>{labelize(r.tag)}</span>
          <span>{r.count} · {r.win_rate}% · <b style={{ color: r.total_pnl >= 0 ? "var(--green)" : "var(--red)" }}>${r.total_pnl}</b></span>
        </div>
      ))}
    </div>
  );
}
