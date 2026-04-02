import { useState, useEffect } from "react";
import { api, AnalyticsData } from "../api";

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [days, setDays] = useState(14);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const d = await api.getAnalytics(days);
    setData(d);
    setLoading(false);
  };

  useEffect(() => { load(); }, [days]);

  if (loading || !data) return <p className="text-2 text-sm">Loading analytics...</p>;

  const pnlColor = data.total_pnl >= 0 ? "var(--green)" : "var(--red)";

  return (
    <div>
      <div className="flex between center mb-3">
        <h2 style={{ fontSize: 16 }}>Strategy Analytics</h2>
        <div className="flex gap-2">
          {[7, 14, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`btn btn-sm ${days === d ? "btn-primary" : "btn-ghost"}`}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Overview Stats */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{data.total_trades}</div>
          <div className="stat-label">Total Trades</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: data.win_rate >= 50 ? "var(--green)" : "var(--red)" }}>
            {data.win_rate}%
          </div>
          <div className="stat-label">Win Rate ({data.wins}W / {data.losses}L)</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: pnlColor }}>
            {data.total_pnl >= 0 ? "+" : ""}{data.total_pnl}
          </div>
          <div className="stat-label">Total P/L</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.avg_score}</div>
          <div className="stat-label">Avg Setup Score</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.avg_rr}</div>
          <div className="stat-label">Avg R:R</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--blue)" }}>{data.open_trades}</div>
          <div className="stat-label">Open Trades</div>
        </div>
      </div>

      {/* Score vs Outcome - KEY insight for strategy improvement */}
      {Object.keys(data.score_analysis).length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: 14, marginBottom: 12 }}>Score vs Outcome (Does your checklist predict winners?)</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={{ textAlign: "left", padding: "8px 0", color: "var(--text2)", fontWeight: 500 }}>Grade</th>
                <th style={{ textAlign: "right", padding: "8px 0", color: "var(--text2)", fontWeight: 500 }}>Trades</th>
                <th style={{ textAlign: "right", padding: "8px 0", color: "var(--text2)", fontWeight: 500 }}>Win Rate</th>
                <th style={{ textAlign: "right", padding: "8px 0", color: "var(--text2)", fontWeight: 500 }}>Avg P/L</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.score_analysis).map(([bucket, stats]) => (
                <tr key={bucket} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "8px 0", fontWeight: 500 }}>{bucket}</td>
                  <td style={{ textAlign: "right", padding: "8px 0" }}>{stats.count}</td>
                  <td style={{ textAlign: "right", padding: "8px 0", color: stats.win_rate >= 50 ? "var(--green)" : "var(--red)" }}>
                    {stats.win_rate}%
                  </td>
                  <td style={{ textAlign: "right", padding: "8px 0", color: stats.avg_pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                    {stats.avg_pnl >= 0 ? "+" : ""}{stats.avg_pnl}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-2 mt-2">
            If A+ setups have a higher win rate than C setups, your checklist is working. If not, revisit your criteria weights.
          </p>
        </div>
      )}

      {/* Direction Breakdown */}
      <div className="card">
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Long vs Short Performance</h3>
        <div className="flex gap-3">
          {Object.entries(data.direction_stats).map(([dir, stats]) => (
            <div key={dir} className="grow" style={{
              padding: 12, borderRadius: 8,
              background: dir === "LONG" ? "var(--green-bg)" : "var(--red-bg)",
              border: `1px solid ${dir === "LONG" ? "var(--green)" : "var(--red)"}`,
            }}>
              <div className="font-500" style={{ color: dir === "LONG" ? "var(--green)" : "var(--red)" }}>{dir}</div>
              <div className="text-sm mt-2">{stats.count} trades</div>
              <div className="text-sm">Win rate: {stats.win_rate}%</div>
              <div className="text-sm">P/L: {stats.pnl >= 0 ? "+" : ""}{stats.pnl}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Pair Breakdown */}
      {Object.keys(data.pair_breakdown).length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: 14, marginBottom: 12 }}>Per-Pair Performance</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={{ textAlign: "left", padding: "8px 0", color: "var(--text2)", fontWeight: 500 }}>Pair</th>
                <th style={{ textAlign: "right", padding: "8px 0", color: "var(--text2)", fontWeight: 500 }}>W</th>
                <th style={{ textAlign: "right", padding: "8px 0", color: "var(--text2)", fontWeight: 500 }}>L</th>
                <th style={{ textAlign: "right", padding: "8px 0", color: "var(--text2)", fontWeight: 500 }}>P/L</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.pair_breakdown)
                .sort(([, a], [, b]) => b.pnl - a.pnl)
                .map(([pair, stats]) => (
                  <tr key={pair} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "8px 0", fontWeight: 500 }}>{pair}</td>
                    <td style={{ textAlign: "right", padding: "8px 0", color: "var(--green)" }}>{stats.wins}</td>
                    <td style={{ textAlign: "right", padding: "8px 0", color: "var(--red)" }}>{stats.losses}</td>
                    <td style={{ textAlign: "right", padding: "8px 0", fontWeight: 500, color: stats.pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                      {stats.pnl >= 0 ? "+" : ""}{stats.pnl}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Recent Lessons */}
      {data.trades.filter(t => t.lessons).length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: 14, marginBottom: 12 }}>Recent Lessons</h3>
          {data.trades.filter(t => t.lessons).slice(0, 10).map(t => (
            <div key={t.id} style={{
              padding: "8px 12px", borderRadius: 8, marginBottom: 6,
              background: "var(--bg3)", borderLeft: `3px solid ${t.status === "win" ? "var(--green)" : "var(--red)"}`,
            }}>
              <div className="text-xs font-500">{t.pair} {t.direction} &mdash; {t.status?.toUpperCase()}</div>
              <div className="text-xs text-2 mt-2" style={{ fontStyle: "italic" }}>{t.lessons}</div>
            </div>
          ))}
        </div>
      )}

      {data.closed_trades === 0 && (
        <div className="card" style={{ textAlign: "center" }}>
          <p className="text-2">No closed trades in the last {days} days.</p>
          <p className="text-xs text-2 mt-2">Log trades and add results to start seeing analytics.</p>
        </div>
      )}
    </div>
  );
}
