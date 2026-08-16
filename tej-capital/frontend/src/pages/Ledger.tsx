import { useState } from "react";
import { useAccounts, type Account } from "../hooks/useAccounts";
import { useLedgerYear } from "../hooks/useLedger";
import { EmptyState } from "../components/EmptyState";
import { YearLedger } from "../components/YearLedger";
import { SectionHeader } from "../components/SectionHeader";
import { Button } from "../components/Button";

export default function Ledger() {
  const { data: accounts, isLoading: accountsLoading } = useAccounts();
  const [accountId, setAccountId] = useState<string>();
  const activeId = accountId ?? accounts?.[0]?.id;

  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);

  const ledger = useLedgerYear(activeId, year);

  if (!accountsLoading && !accounts?.length) {
    return (
      <EmptyState
        title="No accounts yet"
        body="Add an account first (Accounts tab) so we know where your closing equity is coming from."
        cta={{ label: "Add account", to: "/accounts" }}
      />
    );
  }

  if (!activeId) {
    return <EmptyState title="Ledger" body="Loading accounts…" />;
  }

  const s = ledger.stats;
  const hasAnyMarks = ledger.marks.length > 0;

  return (
    <div>
      <SectionHeader
        title="Ledger"
        action={
          <div className="year-switcher">
            {accounts && accounts.length > 1 && (
              <AccountPicker accounts={accounts} value={activeId} onChange={setAccountId} />
            )}
            <Button variant="secondary" onClick={() => setYear((y) => y - 1)}>
              ←
            </Button>
            <span>{year}</span>
            <Button variant="secondary" onClick={() => setYear((y) => y + 1)} disabled={year >= currentYear}>
              →
            </Button>
          </div>
        }
      />

      <div className="streak-row">
        <div className="streak-card streak-card--primary">
          <div className="streak-card__label">Discipline streak</div>
          <div className="streak-card__value">{s.longestMarkedStreak}</div>
        </div>
        <div className="streak-card">
          <div className="streak-card__label">Longest green run</div>
          <div className="streak-card__value">{s.longestGreenRun}</div>
        </div>
        <div className="streak-card">
          <div className="streak-card__label">Longest red run</div>
          <div className="streak-card__value">{s.longestRedRun}</div>
        </div>
      </div>

      {hasAnyMarks ? (
        <YearLedger year={year} marks={ledger.marks} />
      ) : (
        <EmptyState
          title="No marks yet"
          body="Enter today's closing equity and your record begins. Everything on every other screen is built from this one number, entered every day."
          cta={{ label: "Go to Today", to: "/" }}
        />
      )}

      {hasAnyMarks && (
        <p className="ledger-footer">
          {s.markedDays} marked days · {s.greenDays} green · {s.redDays} red · {s.daysWithoutMark} days without a
          mark
        </p>
      )}
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
    <select
      className="field__input"
      name="account_id"
      aria-label="Account"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {accounts.map((a) => (
        <option key={a.id} value={a.id}>
          {a.name}
        </option>
      ))}
    </select>
  );
}
