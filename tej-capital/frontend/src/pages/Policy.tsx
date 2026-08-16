import { useMemo, useState } from "react";
import {
  usePolicyLimits, usePolicyBreaches, usePolicyDocument, useSetLimit, usePatchDocument,
  isAmendmentBlocked, LIMIT_TYPES, POLICY_SECTIONS,
  type LimitType, type LimitUnit, type PolicySection, type PolicyLimit, type LimitBreach,
} from "../hooks/usePolicy";
import { useLiveTearsheet } from "../hooks/useMetrics";
import { useTrades } from "../hooks/useTrades";
import { SectionHeader } from "../components/SectionHeader";
import { Button } from "../components/Button";
import { TextField, SelectField, TextareaField } from "../components/TextField";
import { DrawdownAmendmentModal } from "../components/DrawdownAmendmentModal";
import { EmptyState } from "../components/EmptyState";
import { pct, money, todayISO } from "../lib/format";

const LIMIT_LABELS: Record<LimitType, string> = {
  risk_per_trade: "Risk per trade", concurrent_open_risk: "Concurrent open risk",
  daily_loss: "Daily loss", weekly_loss: "Weekly loss", monthly_loss: "Monthly loss",
  drawdown_killswitch: "Drawdown killswitch", asset_class_concentration: "Asset class concentration",
  risk_sizing_consistency: "Risk sizing consistency", avg_loser_vs_1r: "Average loser vs 1R",
  rule_compliance_rate: "Rule compliance rate",
};

const SECTION_LABELS: Record<PolicySection, string> = {
  mandate: "Mandate", method: "Method", time_horizon: "Time horizon", position_sizing: "Position sizing",
  correlation: "Correlation", stop_discipline: "Stop discipline", news_policy: "News policy",
  leverage: "Leverage", valuation: "Valuation", custody: "Custody",
  amendment_procedure: "Amendment procedure", review_cadence: "Review cadence",
};

function fmtThreshold(threshold: string, unit: LimitUnit): string {
  const v = Number(threshold);
  if (unit === "pct") return pct(v);
  if (unit === "r") return `${v}R`;
  return money(v);
}

export default function Policy() {
  const limits = usePolicyLimits();
  const breaches = usePolicyBreaches();
  const doc = usePolicyDocument();
  const tearsheet = useLiveTearsheet("composite");
  const trades = useTrades();
  const setLimit = useSetLimit();
  const patchDoc = usePatchDocument();

  const [editingType, setEditingType] = useState<LimitType | null>(null);
  const [blocked, setBlocked] = useState<{ limitType: LimitType; hint: string; form: FormState } | null>(null);

  const byType = useMemo(() => {
    const m = new Map<LimitType, PolicyLimit>();
    (limits.data ?? []).forEach((l) => m.set(l.limit_type, l));
    return m;
  }, [limits.data]);

  const openBreachByLimitId = useMemo(() => {
    const m = new Map<string, LimitBreach>();
    (breaches.data ?? []).filter((b) => !b.resolved_on).forEach((b) => m.set(b.limit_id, b));
    return m;
  }, [breaches.data]);

  const compliancePct = useMemo(() => {
    const rows = trades.data ?? [];
    const scored = rows.filter((t) => t.rule_compliant != null);
    if (!scored.length) return null;
    return scored.filter((t) => t.rule_compliant === true).length / scored.length;
  }, [trades.data]);

  function currentValueFor(type: LimitType): string {
    if (type === "drawdown_killswitch") return pct(tearsheet.data?.risk.current_drawdown.value ?? null);
    if (type === "rule_compliance_rate") return pct(compliancePct);
    return "—";
  }

  async function submitAmend(limitType: LimitType, form: FormState, override?: { reason: string }) {
    const body = {
      threshold: form.threshold, unit: form.unit, effective_from: form.effectiveFrom,
      committed_action: form.committedAction,
      reason: override ? override.reason : form.reason,
      override_during_drawdown: !!override,
    };
    try {
      await setLimit.mutateAsync({ limitType, body });
      setEditingType(null);
      setBlocked(null);
    } catch (e) {
      const err = e as { status?: number; body?: unknown };
      if (err.status === 409 && isAmendmentBlocked(err.body)) {
        setBlocked({ limitType, hint: err.body.detail.hint, form });
      }
    }
  }

  if (limits.isLoading) {
    return <EmptyState title="Risk Policy" body="Loading policy limits…" />;
  }

  return (
    <div>
      <SectionHeader title="Risk Policy" />

      <div className="page-section">
        <table className="data-table">
          <thead>
            <tr><th>Limit</th><th>Threshold</th><th>Current</th><th>Status</th><th>Committed action</th><th /></tr>
          </thead>
          <tbody>
            {LIMIT_TYPES.map((type) => {
              const l = byType.get(type);
              const breach = l ? openBreachByLimitId.get(l.id) : undefined;
              return (
                <tr key={type}>
                  <td>{LIMIT_LABELS[type]}</td>
                  <td className="data-table__num">{l ? fmtThreshold(l.threshold, l.unit) : "not set"}</td>
                  <td className="data-table__num">{currentValueFor(type)}</td>
                  <td>
                    <span className={`chip ${breach ? "chip--breach" : "chip--ok"}`}>{breach ? "BREACH" : "OK"}</span>
                  </td>
                  <td>{breach ? (l?.committed_action ?? "—") : (l?.committed_action ?? "—")}</td>
                  <td>
                    <Button variant="secondary" onClick={() => setEditingType(type)}>Amend</Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {editingType && (
        <AmendForm
          limitType={editingType}
          current={byType.get(editingType)}
          submitting={setLimit.isPending}
          onCancel={() => setEditingType(null)}
          onSubmit={(form) => submitAmend(editingType, form)}
        />
      )}

      <DrawdownAmendmentModal
        open={!!blocked}
        hint={blocked?.hint ?? ""}
        submitting={setLimit.isPending}
        onCancel={() => setBlocked(null)}
        onConfirm={(reason) => blocked && submitAmend(blocked.limitType, blocked.form, { reason })}
      />

      <SectionHeader title="Investment Policy Statement" />
      <div className="page-section">
        {POLICY_SECTIONS.map((section) => (
          <DocumentSection
            key={section}
            section={section}
            label={SECTION_LABELS[section]}
            body={doc.data?.find((d) => d.section === section)?.body ?? ""}
            onSave={(body) => patchDoc.mutate({ section, body })}
            saving={patchDoc.isPending}
          />
        ))}
      </div>
    </div>
  );
}

type FormState = { threshold: string; unit: LimitUnit; effectiveFrom: string; committedAction: string; reason: string };

function AmendForm({ limitType, current, submitting, onCancel, onSubmit }: {
  limitType: LimitType; current: PolicyLimit | undefined; submitting: boolean;
  onCancel: () => void; onSubmit: (form: FormState) => void;
}) {
  const [form, setForm] = useState<FormState>({
    threshold: current?.threshold ?? "", unit: current?.unit ?? "pct",
    effectiveFrom: todayISO(), committedAction: current?.committed_action ?? "", reason: "",
  });
  return (
    <form
      className="card page-section"
      onSubmit={(e) => { e.preventDefault(); onSubmit(form); }}
    >
      <div className="form-row">
        <TextField label="Threshold" value={form.threshold} onChange={(e) => setForm({ ...form, threshold: e.target.value })} required />
        <SelectField label="Unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value as LimitUnit })}>
          <option value="pct">Percent</option>
          <option value="r">R multiple</option>
          <option value="abs">Absolute</option>
        </SelectField>
      </div>
      <TextField label="Effective from" type="date" value={form.effectiveFrom} onChange={(e) => setForm({ ...form, effectiveFrom: e.target.value })} required />
      <TextareaField label="Committed action on breach" value={form.committedAction} onChange={(e) => setForm({ ...form, committedAction: e.target.value })} required />
      <TextareaField label="Reason for this amendment" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} helperText="Minimum 10 characters" required />
      <div className="form-actions">
        <Button variant="secondary" type="button" onClick={onCancel}>Cancel</Button>
        <Button type="submit" disabled={submitting}>Save {LIMIT_LABELS[limitType]}</Button>
      </div>
    </form>
  );
}

function DocumentSection({ section, label, body, onSave, saving }: {
  section: PolicySection; label: string; body: string; onSave: (body: string) => void; saving: boolean;
}) {
  const [value, setValue] = useState(body);
  const dirty = value !== body;
  return (
    <div className="card page-section" key={section}>
      <TextareaField label={label} value={value} onChange={(e) => setValue(e.target.value)} rows={4} />
      <Button variant="secondary" disabled={!dirty || saving} onClick={() => onSave(value)}>
        {saving ? "Saving…" : "Save section"}
      </Button>
    </div>
  );
}
