import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useAccounts, type Account } from "../hooks/useAccounts";
import { useNav, useSubmitMark, useCorrectMark } from "../hooks/useNav";
import { useCreateFlow, type FlowType } from "../hooks/useFlows";
import { useLedgerYear, findMissedDays } from "../hooks/useLedger";
import { EmptyState } from "../components/EmptyState";
import { YearLedger } from "../components/YearLedger";
import { Button } from "../components/Button";
import { TextField, SelectField, TextareaField } from "../components/TextField";
import { SectionHeader } from "../components/SectionHeader";
import { api } from "../lib/api";
import { formatDateLong, money, pct, shiftISODate, todayISO } from "../lib/format";

const FLOW_TYPE_OPTIONS: { value: FlowType; label: string }[] = [
  { value: "deposit", label: "Deposit" },
  { value: "withdrawal", label: "Withdrawal" },
  { value: "prop_payout", label: "Prop payout" },
  { value: "platform_fee", label: "Platform fee" },
  { value: "transfer_in", label: "Transfer in" },
  { value: "transfer_out", label: "Transfer out" },
];

const CORRECTION_REASON_ERROR =
  "Correction reason must be at least 10 characters. Say what changed and why — that's the audit trail.";

const NO_MARKS_YET_COPY =
  "No marks yet. Enter today's closing equity and your record begins. Everything on every other screen is built from this one number, entered every day.";

function missedDaysCopy(missed: string[]): string {
  const formatted = missed.map(formatDateLong);
  const joined =
    formatted.length <= 1
      ? formatted.join("")
      : formatted.length === 2
        ? `${formatted[0]} and ${formatted[1]}`
        : `${formatted.slice(0, -1).join(", ")}, and ${formatted[formatted.length - 1]}`;
  return (
    `${missed.length} days without a mark — ${joined}. Backfill them or leave them blank; ` +
    `blank days are excluded from your statistics, not counted as flat.`
  );
}

type Breach = { limit_id: string; breached_on: string };
type Limit = { id: string; limit_type: string };

type Confirmation = {
  returnPct: number | null;
  vsPeak: number;
  isNewPeak: boolean;
  breachedLimitTypes: string[];
};

export default function Today() {
  const { data: accounts, isLoading: accountsLoading } = useAccounts();
  const [accountId, setAccountId] = useState<string>();
  const activeId = accountId ?? accounts?.[0]?.id;
  const year = new Date().getFullYear();

  // Full history for this account drives the empty state, the mark-exists /
  // correction check, peak equity, and the missed-days window. A solo
  // trader's history is small enough that fetching it all is fine.
  const { data: history } = useNav(activeId);
  const ledger = useLedgerYear(activeId, year);

  const [asOfDate, setAsOfDate] = useState(todayISO());
  const [closingEquity, setClosingEquity] = useState("");
  const [flowAmount, setFlowAmount] = useState("");
  const [flowType, setFlowType] = useState<FlowType>("deposit");
  const [openRisk, setOpenRisk] = useState("");
  const [ruleBreak, setRuleBreak] = useState<"" | "yes" | "no">("");
  const [ruleDetail, setRuleDetail] = useState("");
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  const [reasonTouched, setReasonTouched] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [missedDaysBanner, setMissedDaysBanner] = useState<string | null>(null);

  const submitMark = useSubmitMark(activeId);
  const correctMark = useCorrectMark(activeId);
  const createFlow = useCreateFlow(activeId);

  const existingForDate = useMemo(
    () => history?.find((m) => m.as_of_date === asOfDate),
    [history, asOfDate],
  );
  const isCorrection = !!existingForDate;

  // Prefill the equity field with the value on file when the selected date
  // already has a mark, so correction mode shows what it's replacing.
  useEffect(() => {
    setClosingEquity(existingForDate ? existingForDate.closing_equity : "");
    setReason("");
    setReasonTouched(false);
  }, [existingForDate]);

  const saving = submitMark.isPending || correctMark.isPending || createFlow.isPending;
  const noAccounts = !accountsLoading && !accounts?.length;
  const firstEverUse = !!history && history.length === 0;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitError(null);

    if (isCorrection && reason.trim().length < 10) {
      setReasonTouched(true);
      return;
    }
    if (!activeId) return;

    const previousMark = (history ?? [])
      .filter((m) => m.as_of_date < asOfDate)
      .sort((a, b) => (a.as_of_date < b.as_of_date ? -1 : 1))
      .at(-1);
    const priorPeak = (history ?? []).reduce((max, m) => Math.max(max, Number(m.closing_equity)), 0);

    let breachesBefore: Breach[] = [];
    try {
      breachesBefore = await api.get<Breach[]>("/policy/breaches");
    } catch {
      breachesBefore = [];
    }

    try {
      if (isCorrection && existingForDate) {
        await correctMark.mutateAsync({ as_of_date: asOfDate, closing_equity: closingEquity, reason });
      } else {
        try {
          await submitMark.mutateAsync({ as_of_date: asOfDate, closing_equity: closingEquity });
        } catch (err) {
          const status = (err as { status?: number }).status;
          if (status === 409) {
            setSubmitError("A mark already exists for this date. Reloading it for correction.");
            return;
          }
          throw err;
        }
      }

      if (flowAmount.trim() !== "" && Number(flowAmount) !== 0) {
        await createFlow.mutateAsync({
          as_of_date: asOfDate,
          amount: flowAmount,
          flow_type: flowType,
          note: note.trim() || null,
        });
      }

      const journalLines: string[] = [];
      if (openRisk.trim() !== "") journalLines.push(`Open risk right now: ${openRisk}`);
      if (ruleBreak) journalLines.push(`Did you break a rule today?: ${ruleBreak === "yes" ? "Yes" : "No"}`);
      if (ruleBreak === "yes" && ruleDetail.trim())
        journalLines.push(`What rule and what triggered it: ${ruleDetail.trim()}`);
      if (note.trim()) journalLines.push(`Today's note: ${note.trim()}`);
      if (journalLines.length > 0) {
        await api.post("/journal", {
          entry_date: asOfDate,
          body: journalLines.join("\n"),
          tags: ruleBreak === "yes" ? ["daily-mark", "rule-break"] : ["daily-mark"],
        });
      }

      let breachedLimitTypes: string[] = [];
      try {
        const [breachesAfter, limits] = await Promise.all([
          api.get<Breach[]>("/policy/breaches"),
          api.get<Limit[]>("/policy/limits"),
        ]);
        const beforeIds = new Set(breachesBefore.map((b) => b.limit_id + b.breached_on));
        const newBreaches = breachesAfter.filter((b) => !beforeIds.has(b.limit_id + b.breached_on));
        const limitTypeById = new Map(limits.map((l) => [l.id, l.limit_type]));
        breachedLimitTypes = newBreaches.map((b) => limitTypeById.get(b.limit_id) ?? "limit");
      } catch {
        breachedLimitTypes = [];
      }

      const equity = Number(closingEquity);
      const peak = Math.max(priorPeak, equity);
      const returnPct = previousMark
        ? (equity - Number(previousMark.closing_equity)) / Number(previousMark.closing_equity)
        : null;

      setConfirmation({
        returnPct,
        vsPeak: peak !== 0 ? (equity - peak) / peak : 0,
        isNewPeak: equity >= peak,
        breachedLimitTypes,
      });

      const bannerKey = `tej-capital:missed-days-banner-shown:${activeId}`;
      if (!localStorage.getItem(bannerKey)) {
        const windowStart = shiftISODate(todayISO(), -14);
        const marked = new Set([...(history ?? []).map((m) => m.as_of_date), asOfDate]);
        const missed = findMissedDays(marked, windowStart, todayISO());
        if (missed.length > 0) {
          setMissedDaysBanner(missedDaysCopy(missed));
          localStorage.setItem(bannerKey, "1");
        }
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Could not save. Try again.");
    }
  }

  if (noAccounts) {
    return (
      <EmptyState
        title="No accounts yet"
        body="Add an account first (Accounts tab) so we know where your closing equity is coming from."
        cta={{ label: "Add account", to: "/accounts" }}
      />
    );
  }

  if (!activeId) {
    return <EmptyState title="Today" body="Loading accounts…" />;
  }

  return (
    <div className="today-layout">
      <form className="today-layout__form" onSubmit={handleSubmit}>
        {accounts && accounts.length > 1 && (
          <AccountPicker accounts={accounts} value={activeId} onChange={setAccountId} />
        )}

        {firstEverUse && !confirmation && (
          <div className="banner banner--info" role="status">
            {NO_MARKS_YET_COPY}
          </div>
        )}

        {isCorrection && (
          <div className="banner banner--correction" role="status">
            This will be recorded as a correction. The original entry stays in the log.
          </div>
        )}

        <TextField
          label="Date"
          name="as_of_date"
          type="date"
          required
          value={asOfDate}
          max={todayISO()}
          onChange={(e) => setAsOfDate(e.target.value)}
        />

        <TextField
          label="Closing equity"
          name="closing_equity"
          type="number"
          inputMode="decimal"
          step="0.01"
          min="0.01"
          required
          placeholder="0.00"
          value={closingEquity}
          onChange={(e) => setClosingEquity(e.target.value)}
          helperText={
            isCorrection && existingForDate
              ? `Currently on file: ${money(Number(existingForDate.closing_equity))}`
              : "The account's total equity at today's close."
          }
        />

        {isCorrection && (
          <TextareaField
            label="Reason for correction"
            name="correction_reason"
            required
            rows={3}
            placeholder="What changed and why"
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              setReasonTouched(true);
            }}
            error={reasonTouched && reason.trim().length < 10 ? CORRECTION_REASON_ERROR : undefined}
          />
        )}

        <div className="form-row">
          <TextField
            label="Money in or out today"
            name="flow_amount"
            type="number"
            inputMode="decimal"
            step="0.01"
            placeholder="0.00"
            value={flowAmount}
            onChange={(e) => setFlowAmount(e.target.value)}
            helperText="Positive for money in, negative for money out."
          />
          <SelectField
            label="Type of movement"
            name="flow_type"
            value={flowType}
            onChange={(e) => setFlowType(e.target.value as FlowType)}
          >
            {FLOW_TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </SelectField>
        </div>

        <TextField
          label="Open risk right now"
          name="open_risk"
          type="number"
          inputMode="decimal"
          step="0.01"
          placeholder="0.00"
          value={openRisk}
          onChange={(e) => setOpenRisk(e.target.value)}
          helperText="Total dollar risk across positions still open at the close, if any."
        />

        <SelectField
          label="Did you break a rule today?"
          name="rule_break"
          value={ruleBreak}
          onChange={(e) => setRuleBreak(e.target.value as "" | "yes" | "no")}
        >
          <option value="">—</option>
          <option value="no">No</option>
          <option value="yes">Yes</option>
        </SelectField>

        {ruleBreak === "yes" && (
          <TextareaField
            label="What rule and what triggered it"
            name="rule_detail"
            rows={3}
            value={ruleDetail}
            onChange={(e) => setRuleDetail(e.target.value)}
          />
        )}

        <TextareaField
          label="Today's note"
          name="note"
          rows={3}
          placeholder="Anything worth remembering about today"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />

        {submitError && (
          <div className="field__error" role="alert">
            {submitError}
          </div>
        )}

        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save mark"}
        </Button>

        {missedDaysBanner && (
          <div className="banner banner--caution" role="status">
            {missedDaysBanner}
          </div>
        )}

        {confirmation && <ConfirmationCard c={confirmation} />}
      </form>

      <div className="today-layout__ledger">
        <SectionHeader title={`${year}`} />
        {ledger.marks.length > 0 ? (
          <YearLedger year={year} marks={ledger.marks} />
        ) : (
          <p className="field__helper">Marks will appear here as you enter them.</p>
        )}
      </div>
    </div>
  );
}

function AccountPicker({
  accounts,
  value,
  onChange,
}: {
  accounts: Account[];
  value: string | undefined;
  onChange: (id: string) => void;
}) {
  return (
    <SelectField label="Account" name="account_id" value={value} onChange={(e) => onChange(e.target.value)}>
      {accounts.map((a) => (
        <option key={a.id} value={a.id}>
          {a.name}
        </option>
      ))}
    </SelectField>
  );
}

function ConfirmationCard({ c }: { c: Confirmation }) {
  return (
    <div className="confirmation-card" role="status">
      <div className="confirmation-card__row">
        <span className="confirmation-card__label">Today's return</span>
        <span
          className={
            c.returnPct == null
              ? "confirmation-card__value"
              : c.returnPct > 0
                ? "confirmation-card__value confirmation-card__value--gain"
                : c.returnPct < 0
                  ? "confirmation-card__value confirmation-card__value--loss"
                  : "confirmation-card__value"
          }
        >
          {pct(c.returnPct)}
        </span>
      </div>
      <div className="confirmation-card__row">
        <span className="confirmation-card__label">Equity vs last peak</span>
        <span
          className={
            c.isNewPeak
              ? "confirmation-card__value confirmation-card__value--gain"
              : "confirmation-card__value confirmation-card__value--loss"
          }
        >
          {c.isNewPeak ? "New peak" : pct(c.vsPeak)}
        </span>
      </div>
      {c.breachedLimitTypes.length > 0 && (
        <div className="confirmation-card__row">
          <span className="confirmation-card__label">Limit breached</span>
          <span className="chip chip--breach">{c.breachedLimitTypes.join(", ")}</span>
        </div>
      )}
    </div>
  );
}
