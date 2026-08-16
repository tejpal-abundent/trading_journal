import { useMemo, useState, type FormEvent } from "react";
import { useQueries } from "@tanstack/react-query";
import { useAccounts, useCreateAccount, type Account, type AccountType } from "../hooks/useAccounts";
import { api } from "../lib/api";
import { SectionHeader } from "../components/SectionHeader";
import { Button } from "../components/Button";
import { TextField, SelectField, TextareaField } from "../components/TextField";
import { EmptyState } from "../components/EmptyState";
import { money, formatDateLong } from "../lib/format";

type FlowRow = { id: string; account_id: string; as_of_date: string; amount: string; flow_type: string; note: string | null };

const ACCOUNT_TYPE_OPTIONS: { value: AccountType; label: string }[] = [
  { value: "live", label: "Live" }, { value: "prop_funded", label: "Prop funded" },
  { value: "prop_evaluation", label: "Prop evaluation" }, { value: "demo", label: "Demo" },
  { value: "verified_mirror", label: "Verified mirror" },
];

const PROP_INCOME_COPY =
  "Prop income. Excluded from the track record by policy — a prop payout shows you cleared someone's rule set, not that you compound capital.";

export default function Accounts() {
  const { data: accounts, isLoading } = useAccounts();
  const createAccount = useCreateAccount();
  const [showForm, setShowForm] = useState(false);

  const ids = useMemo(() => (accounts ?? []).map((a) => a.id), [accounts]);
  const flowQueries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["flows", id, null],
      queryFn: () => api.get<FlowRow[]>(`/accounts/${id}/flows`),
    })),
  });
  const allFlows = flowQueries.flatMap((q) => q.data ?? []);

  const composite = (accounts ?? []).filter((a) => a.in_composite);
  const propAccounts = (accounts ?? []).filter((a) => a.account_type === "prop_funded" || a.account_type === "prop_evaluation");
  const compositeIds = new Set(composite.map((a) => a.id));

  const netContributed = allFlows
    .filter((f) => compositeIds.has(f.account_id) && f.flow_type !== "prop_payout")
    .reduce((sum, f) => sum + Number(f.amount), 0);
  const propIncome = allFlows
    .filter((f) => f.flow_type === "prop_payout")
    .reduce((sum, f) => sum + Number(f.amount), 0);
  const accountById = new Map((accounts ?? []).map((a) => [a.id, a]));

  if (isLoading) return <EmptyState title="Accounts" body="Loading accounts…" />;

  return (
    <div>
      <SectionHeader
        title="Accounts & Capital"
        action={<Button onClick={() => setShowForm((s) => !s)}>{showForm ? "Cancel" : "Add account"}</Button>}
      />

      {showForm && (
        <AddAccountForm
          submitting={createAccount.isPending}
          onSubmit={async (body) => {
            await createAccount.mutateAsync(body);
            setShowForm(false);
          }}
        />
      )}

      <div className="streak-row">
        <div className="streak-card streak-card--primary">
          <div className="streak-card__label">Net capital contributed</div>
          <div className="streak-card__value">{money(netContributed)}</div>
        </div>
        <div className="streak-card">
          <div className="streak-card__label">Prop income (excluded)</div>
          <div className="streak-card__value">{money(propIncome)}</div>
        </div>
      </div>

      <div className="two-col">
        <div>
          <SectionHeader title="Accounts" />
          {!accounts?.length ? (
            <EmptyState title="No accounts yet" body="Add your first account above." />
          ) : (
            <table className="data-table">
              <thead><tr><th>Name</th><th>Broker</th><th>Type</th><th>Composite</th></tr></thead>
              <tbody>
                {accounts.filter((a) => !propAccounts.includes(a)).map((a) => <AccountRow key={a.id} a={a} />)}
              </tbody>
            </table>
          )}

          {propAccounts.length > 0 && (
            <div className="page-section" style={{ marginTop: "var(--space-6)" }}>
              <SectionHeader title="Prop accounts" />
              <p className="page-lede">{PROP_INCOME_COPY}</p>
              <table className="data-table">
                <thead><tr><th>Name</th><th>Broker</th><th>Type</th></tr></thead>
                <tbody>{propAccounts.map((a) => <AccountRow key={a.id} a={a} hideComposite />)}</tbody>
              </table>
            </div>
          )}
        </div>

        <div>
          <SectionHeader title="Capital movements" />
          {allFlows.length === 0 ? (
            <EmptyState title="No movements yet" body="Deposits, withdrawals, and payouts logged from Today will appear here." />
          ) : (
            <table className="data-table">
              <thead><tr><th>Date</th><th>Account</th><th>Type</th><th>Amount</th></tr></thead>
              <tbody>
                {[...allFlows].sort((a, b) => (a.as_of_date < b.as_of_date ? 1 : -1)).map((f) => (
                  <tr key={f.id}>
                    <td>{formatDateLong(f.as_of_date)}</td>
                    <td>{accountById.get(f.account_id)?.name ?? "—"}</td>
                    <td>{f.flow_type.replace("_", " ")}</td>
                    <td className="data-table__num">{money(Number(f.amount))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function AccountRow({ a, hideComposite }: { a: Account; hideComposite?: boolean }) {
  return (
    <tr>
      <td>{a.name}</td>
      <td>{a.broker}</td>
      <td>{ACCOUNT_TYPE_OPTIONS.find((o) => o.value === a.account_type)?.label ?? a.account_type}</td>
      {!hideComposite && <td>{a.in_composite ? "Yes" : "No"}</td>}
    </tr>
  );
}

function AddAccountForm({ submitting, onSubmit }: {
  submitting: boolean;
  onSubmit: (body: { name: string; broker: string; currency: string; account_type: AccountType; in_composite: boolean; exclusion_reason?: string }) => void;
}) {
  const [name, setName] = useState("");
  const [broker, setBroker] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [accountType, setAccountType] = useState<AccountType>("live");
  const [inComposite, setInComposite] = useState(true);
  const [exclusionReason, setExclusionReason] = useState("");

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    onSubmit({ name, broker, currency, account_type: accountType, in_composite: inComposite, exclusion_reason: inComposite ? undefined : exclusionReason });
  }

  return (
    <form className="card page-section" onSubmit={handleSubmit}>
      <div className="form-row">
        <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <TextField label="Broker" value={broker} onChange={(e) => setBroker(e.target.value)} required />
      </div>
      <div className="form-row">
        <TextField label="Currency" value={currency} maxLength={3} onChange={(e) => setCurrency(e.target.value.toUpperCase())} required />
        <SelectField label="Account type" value={accountType} onChange={(e) => setAccountType(e.target.value as AccountType)}>
          {ACCOUNT_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </SelectField>
      </div>
      <label className="modal__checkbox">
        <input type="checkbox" checked={inComposite} onChange={(e) => setInComposite(e.target.checked)} />
        Include in composite track record
      </label>
      {!inComposite && (
        <TextareaField
          label="Exclusion reason"
          helperText="Minimum 10 characters"
          value={exclusionReason}
          onChange={(e) => setExclusionReason(e.target.value)}
          required
        />
      )}
      <div className="form-actions">
        <Button type="submit" disabled={submitting}>{submitting ? "Saving…" : "Add account"}</Button>
      </div>
    </form>
  );
}
