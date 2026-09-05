import { useEffect, useState, type FormEvent } from "react";
import { useAccounts, type Account } from "../hooks/useAccounts";
import {
  useCreateTrade,
  useEnrichTrade,
  useEnrichmentQueue,
  useOpenTrades,
  useCloseTrade,
  usePlaybookSetups,
  riskLimitHintFrom,
  SESSION_OPTIONS,
  EXEC_GRADE_OPTIONS,
  MIND_STATE_OPTIONS,
  TIMEFRAME_OPTIONS,
  type Direction,
  type Session,
  type ExecGrade,
  type MindState,
  type Timeframe,
  type Trade,
} from "../hooks/useTrades";
import { useNav } from "../hooks/useNav";
import { useSettings } from "../hooks/useSettings";
import { EmptyState } from "../components/EmptyState";
import { SectionHeader } from "../components/SectionHeader";
import { SegmentedControl } from "../components/SegmentedControl";
import { TextField, SelectField, TextareaField } from "../components/TextField";
import { Button } from "../components/Button";
import { num } from "../lib/format";

type Tab = "before" | "after";
type YesNo = "" | "yes" | "no";

function nowLocalDatetime(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toISOOrUndefined(local: string): string | undefined {
  if (!local) return undefined;
  const d = new Date(local);
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
}

/** "Limit for 1m is 0.25% ($37.50 at current equity)" — null when either the
 * threshold or the account's latest equity isn't known yet. */
function tfRiskCaption(
  settings: { risk_by_timeframe: Record<string, string> } | undefined,
  tf: Timeframe,
  latestEquity: number | null,
): string | null {
  const threshold = settings ? Number(settings.risk_by_timeframe[tf]) : NaN;
  if (!Number.isFinite(threshold) || latestEquity == null) return null;
  const dollarLimit = threshold * latestEquity;
  return `Limit for ${tf} is ${(threshold * 100).toFixed(2)}% ($${dollarLimit.toFixed(2)} at current equity)`;
}

export default function TradeEntry() {
  const { data: accounts, isLoading: accountsLoading } = useAccounts();
  const { data: setups } = usePlaybookSetups();
  const { data: enrichmentQueue } = useEnrichmentQueue();
  const { data: openTrades } = useOpenTrades();

  const [accountId, setAccountId] = useState<string>();
  const activeAccountId = accountId ?? accounts?.[0]?.id;

  const { data: navMarks } = useNav(activeAccountId);
  const { data: settings } = useSettings();
  const latestEquity = navMarks && navMarks.length > 0 ? Number(navMarks[navMarks.length - 1].closing_equity) : null;

  const [tab, setTab] = useState<Tab>("before");
  const [showQueue, setShowQueue] = useState(false);
  // When set, the form is in close-mode for this specific open trade.
  // The BEFORE section is hidden and Save calls POST /trades/{id}/close.
  const [closingTrade, setClosingTrade] = useState<Trade | null>(null);

  // BEFORE
  const [instrument, setInstrument] = useState("");
  const [direction, setDirection] = useState<Direction>("long");
  const [setupId, setSetupId] = useState("");
  const [timeframe, setTimeframe] = useState<Timeframe>("1h");
  const [entryPrice, setEntryPrice] = useState("");
  const [stop, setStop] = useState("");
  const [target, setTarget] = useState("");
  const [positionSize, setPositionSize] = useState("");
  const [riskAmount, setRiskAmount] = useState("");
  const [riskTouched, setRiskTouched] = useState(false);
  const [session, setSession] = useState<Session | "">("");
  const [htfAligned, setHtfAligned] = useState<YesNo>("");
  const [thesis, setThesis] = useState("");
  const [openedAt, setOpenedAt] = useState(nowLocalDatetime());

  // AFTER
  const [exitPrice, setExitPrice] = useState("");
  const [closedAt, setClosedAt] = useState("");
  const [grossPnl, setGrossPnl] = useState("");
  const [costs, setCosts] = useState("");
  const [maeR, setMaeR] = useState("");
  const [mfeR, setMfeR] = useState("");
  const [ruleCompliant, setRuleCompliant] = useState<YesNo>("");
  const [breachNote, setBreachNote] = useState("");
  const [executionGrade, setExecutionGrade] = useState<ExecGrade | "">("");
  const [stateOfMind, setStateOfMind] = useState<MindState | "">("");
  const [takeaway, setTakeaway] = useState("");

  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [riskFieldError, setRiskFieldError] = useState<string | null>(null);

  const createTrade = useCreateTrade();
  const closeTrade = useCloseTrade();

  /** Enter close-mode for an open trade. Prefills the AFTER section with
   * defaults (closed_at = now, costs = 0) and switches the tab. Cancel
   * returns to normal new-trade mode via `exitCloseMode()`. */
  function startClosingTrade(t: Trade) {
    setClosingTrade(t);
    setTab("after");
    setExitPrice("");
    setClosedAt(nowLocalDatetime());
    setGrossPnl("");
    setCosts("");
    setMaeR("");
    setMfeR("");
    setRuleCompliant("");
    setBreachNote("");
    setExecutionGrade("");
    setStateOfMind("");
    setTakeaway("");
    setSubmitError(null);
    setStatusMessage(null);
    // Scroll form into view so the trader lands on the AFTER inputs.
    setTimeout(() => {
      const form = document.querySelector<HTMLFormElement>(".trade-entry-form");
      form?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  }

  function exitCloseMode() {
    setClosingTrade(null);
    setTab("before");
    setSubmitError(null);
  }

  // Risk auto-suggestion: stop distance x position size, until the trader
  // edits the field directly.
  useEffect(() => {
    if (riskTouched) return;
    const ep = Number(entryPrice);
    const sp = Number(stop);
    const ps = Number(positionSize);
    if (entryPrice && stop && positionSize && !Number.isNaN(ep) && !Number.isNaN(sp) && !Number.isNaN(ps)) {
      const suggested = Math.abs(ep - sp) * ps;
      if (suggested > 0) setRiskAmount(suggested.toFixed(2));
    }
  }, [entryPrice, stop, positionSize, riskTouched]);

  function resetForm() {
    setInstrument("");
    setDirection("long");
    setSetupId("");
    setTimeframe("1h");
    setEntryPrice("");
    setStop("");
    setTarget("");
    setPositionSize("");
    setRiskAmount("");
    setRiskTouched(false);
    setSession("");
    setHtfAligned("");
    setThesis("");
    setOpenedAt(nowLocalDatetime());
    setExitPrice("");
    setClosedAt("");
    setGrossPnl("");
    setCosts("");
    setMaeR("");
    setMfeR("");
    setRuleCompliant("");
    setBreachNote("");
    setExecutionGrade("");
    setStateOfMind("");
    setTakeaway("");
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitError(null);
    setStatusMessage(null);
    setRiskFieldError(null);
    if (!activeAccountId) return;

    // ─── Close-mode: finalise an existing open trade ───
    if (closingTrade) {
      const closed = toISOOrUndefined(closedAt);
      if (!exitPrice || !grossPnl || !closed) {
        setSubmitError("Exit price, gross P&L, and closed-at are required to close a trade.");
        return;
      }
      try {
        await closeTrade.mutateAsync({
          id: closingTrade.id,
          body: {
            exit_price: exitPrice,
            closed_at: closed,
            gross_pnl: grossPnl,
            costs: costs || "0",
            mae_r: maeR || null,
            mfe_r: mfeR || null,
            rule_compliant: ruleCompliant === "" ? null : ruleCompliant === "yes",
            breach_note: breachNote.trim() || null,
            execution_grade: executionGrade || null,
            state_of_mind: stateOfMind || null,
            one_sentence_takeaway: takeaway.trim() || null,
          },
        });
        setStatusMessage(`Trade closed. ${closingTrade.instrument} ${closingTrade.direction} finalised.`);
        exitCloseMode();
      } catch (err) {
        setSubmitError(err instanceof Error ? err.message : "Could not close the trade.");
      }
      return;
    }

    const opened = toISOOrUndefined(openedAt);
    if (!instrument.trim() || !entryPrice || !positionSize || !opened) {
      setSubmitError("Instrument, direction, entry price, position size, and opened-at are required.");
      return;
    }

    try {
      const result = await createTrade.mutateAsync({
        account_id: activeAccountId,
        instrument: instrument.trim().toUpperCase(),
        direction,
        setup_id: setupId || null,
        timeframe,
        entry_price: entryPrice,
        initial_stop: stop || null,
        target_price: target || null,
        position_size: positionSize,
        risk_amount: riskAmount || null,
        session: session || null,
        htf_aligned: htfAligned === "" ? null : htfAligned === "yes",
        thesis: thesis.trim() || null,
        opened_at: opened,
        exit_price: exitPrice || null,
        closed_at: toISOOrUndefined(closedAt) ?? null,
        gross_pnl: grossPnl || null,
        costs: costs || undefined,
        mae_r: maeR || null,
        mfe_r: mfeR || null,
        rule_compliant: ruleCompliant === "" ? null : ruleCompliant === "yes",
        breach_note: breachNote.trim() || null,
        execution_grade: executionGrade || null,
        state_of_mind: stateOfMind || null,
        one_sentence_takeaway: takeaway.trim() || null,
      });
      setStatusMessage(
        result.enrichment_needed
          ? "Trade saved. Added to the enrichment queue — risk in cash is still missing."
          : "Trade saved.",
      );
      resetForm();
    } catch (err) {
      const riskHint = riskLimitHintFrom(err);
      if (riskHint) {
        setRiskFieldError(riskHint);
      } else {
        setSubmitError(err instanceof Error ? err.message : "Could not save the trade. Try again.");
      }
    }
  }

  if (!accountsLoading && !accounts?.length) {
    return (
      <EmptyState
        title="No accounts yet"
        body="Add an account first (Accounts tab) so trades have somewhere to belong."
        cta={{ label: "Add account", to: "/accounts" }}
      />
    );
  }

  if (!activeAccountId) {
    return <EmptyState title="Trade Entry" body="Loading accounts…" />;
  }

  const queueCount = enrichmentQueue?.length ?? 0;

  return (
    <div>
      <SectionHeader title="Trade Entry" />

      {queueCount > 0 && (
        <button type="button" className="enrichment-link" onClick={() => setShowQueue((v) => !v)}>
          {queueCount} {queueCount === 1 ? "trade needs" : "trades need"} enrichment
        </button>
      )}

      {showQueue && queueCount > 0 && <EnrichmentQueue trades={enrichmentQueue ?? []} />}

      {openTrades && openTrades.length > 0 && (
        <OpenPositionsPanel
          trades={openTrades}
          setups={setups ?? []}
          activeId={closingTrade?.id ?? null}
          onClose={startClosingTrade}
        />
      )}

      {closingTrade && (
        <div className="banner banner--info close-mode-banner" role="status">
          Closing{" "}
          <strong>
            {closingTrade.instrument} {closingTrade.direction}
          </strong>{" "}
          opened {formatOpened(closingTrade.opened_at)} at {closingTrade.entry_price}
          {closingTrade.risk_amount ? ` · risk $${Number(closingTrade.risk_amount).toFixed(2)}` : ""}
          . Fill the exit fields below.{" "}
          <button type="button" className="close-mode-cancel" onClick={exitCloseMode}>
            Cancel
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="form-fieldset trade-entry-form">
        {accounts && accounts.length > 1 && (
          <SelectField
            label="Account"
            name="account_id"
            value={activeAccountId}
            onChange={(e) => setAccountId(e.target.value)}
          >
            {accounts.map((a: Account) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </SelectField>
        )}

        {!closingTrade && (
          <SegmentedControl
            options={[
              { value: "before", label: "Before — thesis" },
              { value: "after", label: "After — outcome" },
            ]}
            value={tab}
            onChange={setTab}
          />
        )}

        {tab === "before" && !closingTrade ? (
          <div className="form-fieldset">
            <div className="form-row">
              <TextField
                label="Instrument"
                name="instrument"
                required
                placeholder="XAUUSD"
                value={instrument}
                onChange={(e) => setInstrument(e.target.value)}
              />
              <SelectField
                label="Direction"
                name="direction"
                value={direction}
                onChange={(e) => setDirection(e.target.value as Direction)}
              >
                <option value="long">Long</option>
                <option value="short">Short</option>
              </SelectField>
            </div>

            <SelectField label="Setup" name="setup_id" value={setupId} onChange={(e) => setSetupId(e.target.value)}>
              <option value="">—</option>
              {(setups ?? [])
                .filter((s) => s.is_active)
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.tag} — {s.name}
                  </option>
                ))}
            </SelectField>

            <SelectField
              label="Timeframe"
              name="timeframe"
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value as Timeframe)}
            >
              {TIMEFRAME_OPTIONS.map((tf) => (
                <option key={tf} value={tf}>
                  {tf}
                </option>
              ))}
            </SelectField>

            <div className="form-row">
              <TextField
                label="Entry price"
                name="entry_price"
                type="number"
                inputMode="decimal"
                step="0.00000001"
                required
                value={entryPrice}
                onChange={(e) => setEntryPrice(e.target.value)}
              />
              <TextField
                label="Stop"
                name="initial_stop"
                type="number"
                inputMode="decimal"
                step="0.00000001"
                value={stop}
                onChange={(e) => setStop(e.target.value)}
              />
            </div>

            <div className="form-row">
              <TextField
                label="Target"
                name="target_price"
                type="number"
                inputMode="decimal"
                step="0.00000001"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              />
              <TextField
                label="Position size"
                name="position_size"
                type="number"
                inputMode="decimal"
                step="0.00000001"
                required
                value={positionSize}
                onChange={(e) => setPositionSize(e.target.value)}
              />
            </div>

            <TextField
              label="Risk in cash"
              name="risk_amount"
              type="number"
              inputMode="decimal"
              step="0.01"
              value={riskAmount}
              onChange={(e) => {
                setRiskAmount(e.target.value);
                setRiskTouched(true);
                setRiskFieldError(null);
              }}
              error={riskFieldError ?? undefined}
              helperText="Auto-suggested from stop distance x position size — editable."
            />
            {!riskFieldError && (timeframe === "1m" || timeframe === "5m") && tfRiskCaption(settings, timeframe, latestEquity) && (
              <p className="field__helper">{tfRiskCaption(settings, timeframe, latestEquity)}</p>
            )}

            <div className="form-row">
              <SelectField
                label="Session"
                name="session"
                value={session}
                onChange={(e) => setSession(e.target.value as Session | "")}
              >
                <option value="">—</option>
                {SESSION_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </SelectField>
              <SelectField
                label="HTF aligned"
                name="htf_aligned"
                value={htfAligned}
                onChange={(e) => setHtfAligned(e.target.value as YesNo)}
              >
                <option value="">—</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </SelectField>
            </div>

            <TextField
              label="Opened at"
              name="opened_at"
              type="datetime-local"
              required
              value={openedAt}
              onChange={(e) => setOpenedAt(e.target.value)}
            />

            <TextareaField
              label="Why this trade"
              name="thesis"
              rows={4}
              value={thesis}
              onChange={(e) => setThesis(e.target.value)}
            />
          </div>
        ) : (
          <div className="form-fieldset">
            <div className="form-row">
              <TextField
                label="Exit price"
                name="exit_price"
                type="number"
                inputMode="decimal"
                step="0.00000001"
                value={exitPrice}
                onChange={(e) => setExitPrice(e.target.value)}
              />
              <TextField
                label="Closed at"
                name="closed_at"
                type="datetime-local"
                value={closedAt}
                onChange={(e) => setClosedAt(e.target.value)}
              />
            </div>

            <div className="form-row">
              <TextField
                label="Gross P&L"
                name="gross_pnl"
                type="number"
                inputMode="decimal"
                step="0.01"
                value={grossPnl}
                onChange={(e) => setGrossPnl(e.target.value)}
              />
              <TextField
                label="Costs"
                name="costs"
                type="number"
                inputMode="decimal"
                step="0.01"
                value={costs}
                onChange={(e) => setCosts(e.target.value)}
              />
            </div>

            <div className="form-row">
              <TextField
                label="MAE (in R)"
                name="mae_r"
                type="number"
                inputMode="decimal"
                step="0.01"
                helperText="Worst point against the trade."
                value={maeR}
                onChange={(e) => setMaeR(e.target.value)}
              />
              <TextField
                label="MFE (in R)"
                name="mfe_r"
                type="number"
                inputMode="decimal"
                step="0.01"
                helperText="Best point in favor."
                value={mfeR}
                onChange={(e) => setMfeR(e.target.value)}
              />
            </div>

            <SelectField
              label="Rule compliant"
              name="rule_compliant"
              value={ruleCompliant}
              onChange={(e) => setRuleCompliant(e.target.value as YesNo)}
            >
              <option value="">—</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </SelectField>

            {ruleCompliant === "no" && (
              <TextareaField
                label="If no, what happened"
                name="breach_note"
                rows={3}
                value={breachNote}
                onChange={(e) => setBreachNote(e.target.value)}
              />
            )}

            <div className="form-row">
              <SelectField
                label="Execution grade"
                name="execution_grade"
                value={executionGrade}
                onChange={(e) => setExecutionGrade(e.target.value as ExecGrade | "")}
              >
                <option value="">—</option>
                {EXEC_GRADE_OPTIONS.map((g) => (
                  <option key={g} value={g}>
                    {g}
                  </option>
                ))}
              </SelectField>
              <SelectField
                label="State of mind"
                name="state_of_mind"
                value={stateOfMind}
                onChange={(e) => setStateOfMind(e.target.value as MindState | "")}
              >
                <option value="">—</option>
                {MIND_STATE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </SelectField>
            </div>

            <TextField
              label="One-sentence takeaway"
              name="one_sentence_takeaway"
              value={takeaway}
              onChange={(e) => setTakeaway(e.target.value)}
            />
          </div>
        )}

        {submitError && (
          <div className="field__error" role="alert">
            {submitError}
          </div>
        )}
        {statusMessage && (
          <div className="banner banner--info" role="status">
            {statusMessage}
          </div>
        )}

        <Button type="submit" disabled={createTrade.isPending || closeTrade.isPending}>
          {closingTrade
            ? closeTrade.isPending ? "Closing…" : "Close trade"
            : createTrade.isPending ? "Saving…" : (tab === "before" ? "Log open trade" : "Save trade")}
        </Button>
      </form>
    </div>
  );
}

/** Panel above the form listing every open trade for the user's accounts.
 * One row per trade with a Close button that flips the main form into
 * close-mode (BEFORE hidden, AFTER shown, save → POST /trades/{id}/close). */
function OpenPositionsPanel({
  trades,
  setups,
  activeId,
  onClose,
}: {
  trades: Trade[];
  setups: { id: string; tag: string; name: string }[];
  activeId: string | null;
  onClose: (t: Trade) => void;
}) {
  const setupsById = new Map(setups.map((s) => [s.id, s]));
  return (
    <section className="open-positions">
      <div className="open-positions__header">
        <span className="open-positions__title">Open positions</span>
        <span className="open-positions__count">
          {trades.length} {trades.length === 1 ? "trade" : "trades"} running
        </span>
      </div>
      <ul className="open-positions__list">
        {trades.map((t) => {
          const setup = t.setup_id ? setupsById.get(t.setup_id) : null;
          return (
            <li
              key={t.id}
              className={"open-positions__row" + (activeId === t.id ? " open-positions__row--active" : "")}
            >
              <div className="open-positions__row-main">
                <span className="open-positions__inst">{t.instrument}</span>
                <span className="open-positions__dir">{t.direction}</span>
                <span className="open-positions__entry">entry {t.entry_price}</span>
                <span className="open-positions__opened">
                  {formatOpened(t.opened_at)} · {daysHeld(t.opened_at)}d held
                </span>
                {setup && <span className="open-positions__setup">{setup.tag}</span>}
                {t.timeframe && <span className="open-positions__tf">{t.timeframe}</span>}
              </div>
              <button
                type="button"
                className="btn btn--secondary open-positions__close-btn"
                onClick={() => onClose(t)}
                disabled={activeId === t.id}
              >
                {activeId === t.id ? "Closing…" : "Close"}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function formatOpened(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function daysHeld(openedIso: string): number {
  const opened = new Date(openedIso).getTime();
  const now = Date.now();
  return Math.max(0, Math.floor((now - opened) / (1000 * 60 * 60 * 24)));
}

function EnrichmentQueue({ trades }: { trades: Trade[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = trades.find((t) => t.id === selectedId) ?? null;

  return (
    <div className="enrichment-queue">
      {trades.map((t) => (
        <div key={t.id} className={selectedId === t.id ? "enrichment-row enrichment-row--active" : "enrichment-row"}>
          <div>
            <strong>{t.instrument}</strong>{" "}
            <span className="enrichment-row__meta">
              {t.direction} · entry {num(Number(t.entry_price))} · opened{" "}
              {new Date(t.opened_at).toLocaleDateString()}
            </span>
          </div>
          <Button variant="secondary" onClick={() => setSelectedId(selectedId === t.id ? null : t.id)}>
            {selectedId === t.id ? "Close" : "Complete"}
          </Button>
        </div>
      ))}
      {selected && <EnrichmentForm trade={selected} onDone={() => setSelectedId(null)} />}
    </div>
  );
}

function EnrichmentForm({ trade, onDone }: { trade: Trade; onDone: () => void }) {
  const enrich = useEnrichTrade();
  const [setupId, setSetupId] = useState(trade.setup_id ?? "");
  const [riskAmount, setRiskAmount] = useState(trade.risk_amount ?? "");
  const [executionGrade, setExecutionGrade] = useState<ExecGrade | "">(trade.execution_grade ?? "");
  const [stateOfMind, setStateOfMind] = useState<MindState | "">(trade.state_of_mind ?? "");
  const [maeR, setMaeR] = useState(trade.mae_r ?? "");
  const [mfeR, setMfeR] = useState(trade.mfe_r ?? "");
  const [ruleCompliant, setRuleCompliant] = useState<YesNo>(
    trade.rule_compliant == null ? "" : trade.rule_compliant ? "yes" : "no",
  );
  const [breachNote, setBreachNote] = useState(trade.breach_note ?? "");
  const [takeaway, setTakeaway] = useState(trade.one_sentence_takeaway ?? "");
  const { data: setups } = usePlaybookSetups();

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    await enrich.mutateAsync({
      id: trade.id,
      body: {
        setup_id: setupId || null,
        risk_amount: riskAmount || null,
        execution_grade: executionGrade || null,
        state_of_mind: stateOfMind || null,
        mae_r: maeR || null,
        mfe_r: mfeR || null,
        rule_compliant: ruleCompliant === "" ? null : ruleCompliant === "yes",
        breach_note: breachNote.trim() || null,
        one_sentence_takeaway: takeaway.trim() || null,
      },
    });
    onDone();
  }

  return (
    <form onSubmit={handleSubmit} className="form-fieldset card">
      <SelectField label="Setup" name="setup_id" value={setupId} onChange={(e) => setSetupId(e.target.value)}>
        <option value="">—</option>
        {(setups ?? [])
          .filter((s) => s.is_active)
          .map((s) => (
            <option key={s.id} value={s.id}>
              {s.tag} — {s.name}
            </option>
          ))}
      </SelectField>
      <TextField
        label="Risk in cash"
        name="risk_amount"
        type="number"
        inputMode="decimal"
        step="0.01"
        value={riskAmount}
        onChange={(e) => setRiskAmount(e.target.value)}
      />
      <div className="form-row">
        <TextField
          label="MAE (in R)"
          name="mae_r"
          type="number"
          inputMode="decimal"
          step="0.01"
          value={maeR}
          onChange={(e) => setMaeR(e.target.value)}
        />
        <TextField
          label="MFE (in R)"
          name="mfe_r"
          type="number"
          inputMode="decimal"
          step="0.01"
          value={mfeR}
          onChange={(e) => setMfeR(e.target.value)}
        />
      </div>
      <SelectField
        label="Rule compliant"
        name="rule_compliant"
        value={ruleCompliant}
        onChange={(e) => setRuleCompliant(e.target.value as YesNo)}
      >
        <option value="">—</option>
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </SelectField>
      {ruleCompliant === "no" && (
        <TextareaField
          label="If no, what happened"
          name="breach_note"
          rows={3}
          value={breachNote}
          onChange={(e) => setBreachNote(e.target.value)}
        />
      )}
      <div className="form-row">
        <SelectField
          label="Execution grade"
          name="execution_grade"
          value={executionGrade}
          onChange={(e) => setExecutionGrade(e.target.value as ExecGrade | "")}
        >
          <option value="">—</option>
          {EXEC_GRADE_OPTIONS.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </SelectField>
        <SelectField
          label="State of mind"
          name="state_of_mind"
          value={stateOfMind}
          onChange={(e) => setStateOfMind(e.target.value as MindState | "")}
        >
          <option value="">—</option>
          {MIND_STATE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </SelectField>
      </div>
      <TextField
        label="One-sentence takeaway"
        name="one_sentence_takeaway"
        value={takeaway}
        onChange={(e) => setTakeaway(e.target.value)}
      />
      <Button type="submit" disabled={enrich.isPending}>
        {enrich.isPending ? "Saving…" : "Save enrichment"}
      </Button>
    </form>
  );
}
