import { useMemo, useState } from "react";
import { useAccounts, type Account } from "../hooks/useAccounts";
import {
  useTrades,
  usePlaybookSetups,
  SESSION_OPTIONS,
  TIMEFRAME_OPTIONS,
  type Trade,
  type Session,
  type Timeframe,
} from "../hooks/useTrades";
import { SectionHeader } from "../components/SectionHeader";
import { EmptyState } from "../components/EmptyState";
import { SegmentedControl } from "../components/SegmentedControl";
import { SelectField, TextField } from "../components/TextField";
import "../design/components.css";

type Status = "all" | "open" | "closed" | "broken";
type SortKey = "opened_at" | "instrument" | "r_multiple" | "gross_pnl";
type SortDir = "asc" | "desc";

const STATUS_OPTIONS: { value: Status; label: string }[] = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "closed", label: "Closed" },
  { value: "broken", label: "Rule broken" },
];

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" });
}

function fmtMoney(v: string | number | null | undefined, currency = "USD"): string {
  if (v == null || v === "") return "—";
  const n = typeof v === "string" ? Number(v) : v;
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(n);
}

function fmtR(v: number | null): string {
  if (v == null) return "—";
  return (v >= 0 ? "+" : "") + v.toFixed(2) + "R";
}

function tradeStatus(t: Trade): "open" | "closed" {
  return t.closed_at ? "closed" : "open";
}

export default function TradeLog() {
  const { data: accounts } = useAccounts();
  const { data: setups } = usePlaybookSetups();

  const [accountId, setAccountId] = useState<string>("all");
  const [status, setStatus] = useState<Status>("all");
  const [setupId, setSetupId] = useState<string>("all");
  const [timeframe, setTimeframe] = useState<Timeframe | "all">("all");
  const [session, setSession] = useState<Session | "all">("all");
  const [since, setSince] = useState<string>(daysAgo(90));
  const [sortKey, setSortKey] = useState<SortKey>("opened_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const scopeAccount = accountId === "all" ? undefined : accountId;
  const { data: trades = [], isLoading } = useTrades(scopeAccount, since);

  const setupsById = useMemo(
    () => new Map((setups ?? []).map((s) => [s.id, s])),
    [setups],
  );

  const filtered = useMemo(() => {
    return trades.filter((t) => {
      if (status === "open" && t.closed_at) return false;
      if (status === "closed" && !t.closed_at) return false;
      if (status === "broken" && t.rule_compliant !== false) return false;
      if (setupId !== "all" && t.setup_id !== setupId) return false;
      if (timeframe !== "all" && t.timeframe !== timeframe) return false;
      if (session !== "all" && t.session !== session) return false;
      return true;
    });
  }, [trades, status, setupId, timeframe, session]);

  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      const av = pickSortValue(a, sortKey);
      const bv = pickSortValue(b, sortKey);
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av).localeCompare(String(bv)) * dir;
    });
    return arr;
  }, [filtered, sortKey, sortDir]);

  const stats = useMemo(() => {
    const closed = filtered.filter((t) => t.closed_at);
    const rs = closed.map((t) => t.r_multiple).filter((r): r is number => r != null);
    const wins = rs.filter((r) => r > 0);
    const losses = rs.filter((r) => r < 0);
    const totalR = rs.reduce((s, r) => s + r, 0);
    const expectancy = rs.length ? totalR / rs.length : null;
    const grossPnl = closed.reduce((s, t) => s + Number(t.gross_pnl ?? 0), 0);
    const grossCosts = closed.reduce((s, t) => s + Number(t.costs ?? 0), 0);
    return {
      count: filtered.length,
      closed: closed.length,
      open: filtered.length - closed.length,
      wins: wins.length,
      losses: losses.length,
      winRate: rs.length ? wins.length / rs.length : null,
      expectancy,
      totalR,
      grossPnl,
      grossCosts,
      netPnl: grossPnl - grossCosts,
    };
  }, [filtered]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const hasMultipleAccounts = accounts && accounts.length > 1;

  return (
    <div>
      <SectionHeader title="Trade Log" />
      <p className="page-lede">Every trade, filtered how you want it. Click a row for the thesis and review.</p>

      <div className="trade-log__filters">
        <SegmentedControl options={STATUS_OPTIONS} value={status} onChange={setStatus} />
        {hasMultipleAccounts && (
          <SelectField label="Account" name="account_id" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
            <option value="all">All accounts</option>
            {(accounts ?? []).map((a: Account) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </SelectField>
        )}
        <SelectField label="Setup" name="setup_id" value={setupId} onChange={(e) => setSetupId(e.target.value)}>
          <option value="all">All setups</option>
          {(setups ?? []).map((s) => (
            <option key={s.id} value={s.id}>{s.tag}</option>
          ))}
        </SelectField>
        <SelectField label="Timeframe" name="timeframe" value={timeframe} onChange={(e) => setTimeframe(e.target.value as Timeframe | "all")}>
          <option value="all">All TF</option>
          {TIMEFRAME_OPTIONS.map((tf) => (
            <option key={tf} value={tf}>{tf}</option>
          ))}
        </SelectField>
        <SelectField label="Session" name="session" value={session} onChange={(e) => setSession(e.target.value as Session | "all")}>
          <option value="all">All sessions</option>
          {SESSION_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </SelectField>
        <TextField label="Since" name="since" type="date" value={since} onChange={(e) => setSince(e.target.value)} />
      </div>

      {isLoading ? (
        <p className="page-lede">Loading trades…</p>
      ) : sorted.length === 0 ? (
        <EmptyState
          title="No trades match these filters"
          body={trades.length === 0 ? "No trades logged in this window. Head to Trade Entry to log your first." : "Widen the filters or push the 'Since' date back."}
          cta={trades.length === 0 ? { label: "Go to Trade Entry", to: "/trades/new" } : undefined}
        />
      ) : (
        <div className="trade-log__scroll">
          <table className="trade-log__table">
            <thead>
              <tr>
                <th className={sortableClass("opened_at", sortKey)} onClick={() => toggleSort("opened_at")}>Opened{sortIndicator("opened_at", sortKey, sortDir)}</th>
                <th>Closed</th>
                <th className={sortableClass("instrument", sortKey)} onClick={() => toggleSort("instrument")}>Instrument{sortIndicator("instrument", sortKey, sortDir)}</th>
                <th>Dir</th>
                <th>TF</th>
                <th>Setup</th>
                <th className="ta-r">Entry</th>
                <th className="ta-r">Exit</th>
                <th className="ta-r">Risk</th>
                <th className={"ta-r " + sortableClass("gross_pnl", sortKey)} onClick={() => toggleSort("gross_pnl")}>P&amp;L{sortIndicator("gross_pnl", sortKey, sortDir)}</th>
                <th className={"ta-r " + sortableClass("r_multiple", sortKey)} onClick={() => toggleSort("r_multiple")}>R{sortIndicator("r_multiple", sortKey, sortDir)}</th>
                <th>Rule</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((t) => {
                const setup = t.setup_id ? setupsById.get(t.setup_id) : null;
                const stat = tradeStatus(t);
                const rNum = t.r_multiple;
                const rowClass = "trade-log__row" + (expandedId === t.id ? " trade-log__row--expanded" : "");
                return [
                  <tr key={t.id} className={rowClass} onClick={() => setExpandedId(expandedId === t.id ? null : t.id)}>
                    <td className="trade-log__date">{fmtDate(t.opened_at)}</td>
                    <td className="trade-log__date">{fmtDate(t.closed_at)}</td>
                    <td className="trade-log__inst">{t.instrument}</td>
                    <td><span className={"chip chip--" + (t.direction === "long" ? "ok" : "breach")}>{t.direction}</span></td>
                    <td>{t.timeframe ?? "—"}</td>
                    <td className="trade-log__setup">{setup?.tag ?? "—"}</td>
                    <td className="ta-r trade-log__num">{t.entry_price}</td>
                    <td className="ta-r trade-log__num">{t.exit_price ?? "—"}</td>
                    <td className="ta-r trade-log__num">{fmtMoney(t.risk_amount)}</td>
                    <td className={"ta-r trade-log__num " + pnlClass(t.gross_pnl)}>{fmtMoney(t.gross_pnl)}</td>
                    <td className={"ta-r trade-log__num " + rClass(rNum)}>{fmtR(rNum)}</td>
                    <td>{t.rule_compliant == null ? "—" : t.rule_compliant ? "✓" : "✗"}</td>
                    <td><span className={"chip chip--" + (stat === "open" ? "neutral" : "ok")}>{stat}</span></td>
                  </tr>,
                  expandedId === t.id ? (
                    <tr key={t.id + "-detail"} className="trade-log__detail-row">
                      <td colSpan={13}>
                        <div className="trade-log__detail">
                          {t.thesis && (
                            <div><span className="trade-log__detail-label">Thesis</span><p>{t.thesis}</p></div>
                          )}
                          {t.review && (
                            <div><span className="trade-log__detail-label">Review</span><p>{t.review}</p></div>
                          )}
                          {t.one_sentence_takeaway && (
                            <div><span className="trade-log__detail-label">Takeaway</span><p>{t.one_sentence_takeaway}</p></div>
                          )}
                          {t.breach_note && (
                            <div><span className="trade-log__detail-label">Breach note</span><p>{t.breach_note}</p></div>
                          )}
                          <div className="trade-log__detail-meta">
                            {t.session && <span>Session · {t.session}</span>}
                            {t.htf_aligned != null && <span>HTF · {t.htf_aligned ? "aligned" : "not aligned"}</span>}
                            {t.execution_grade && <span>Grade · {t.execution_grade}</span>}
                            {t.state_of_mind && <span>Mind · {t.state_of_mind}</span>}
                            {t.mae_r && <span>MAE · {t.mae_r}R</span>}
                            {t.mfe_r && <span>MFE · {t.mfe_r}R</span>}
                            {t.initial_stop && <span>Stop · {t.initial_stop}</span>}
                            {t.position_size && <span>Size · {t.position_size}</span>}
                          </div>
                        </div>
                      </td>
                    </tr>
                  ) : null,
                ];
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="trade-log__footer">
        <span>Total <strong>{stats.count}</strong></span>
        <span>Closed <strong>{stats.closed}</strong></span>
        <span>Open <strong>{stats.open}</strong></span>
        <span>Win rate <strong>{stats.winRate == null ? "—" : (stats.winRate * 100).toFixed(0) + "%"}</strong></span>
        <span>Expectancy <strong>{stats.expectancy == null ? "—" : fmtR(stats.expectancy)}</strong></span>
        <span>Total R <strong>{fmtR(stats.totalR)}</strong></span>
        <span>Net P&amp;L <strong className={stats.netPnl >= 0 ? "trade-log__pnl-gain" : "trade-log__pnl-loss"}>{fmtMoney(stats.netPnl)}</strong></span>
      </div>
    </div>
  );
}

function pickSortValue(t: Trade, key: SortKey): string | number | null {
  if (key === "opened_at") return t.opened_at;
  if (key === "instrument") return t.instrument;
  if (key === "r_multiple") return t.r_multiple;
  if (key === "gross_pnl") return t.gross_pnl == null ? null : Number(t.gross_pnl);
  return null;
}

function sortableClass(col: SortKey, active: SortKey): string {
  return "trade-log__sortable" + (col === active ? " trade-log__sortable--active" : "");
}

function sortIndicator(col: SortKey, active: SortKey, dir: SortDir): string {
  if (col !== active) return "";
  return dir === "asc" ? " ↑" : " ↓";
}

function pnlClass(v: string | null): string {
  if (v == null) return "";
  const n = Number(v);
  if (!Number.isFinite(n) || n === 0) return "";
  return n > 0 ? "trade-log__pnl-gain" : "trade-log__pnl-loss";
}

function rClass(v: number | null): string {
  if (v == null || v === 0) return "";
  return v > 0 ? "trade-log__pnl-gain" : "trade-log__pnl-loss";
}
