import { useEffect, useState, type FormEvent } from "react";
import { useSettings, useUpdateSettings, useTargets, useUpsertTarget, type Settings as SettingsT } from "../hooks/useSettings";
import { TIMEFRAME_OPTIONS, type Timeframe } from "../hooks/useTrades";
import { SectionHeader } from "../components/SectionHeader";
import { Button } from "../components/Button";
import { TextField } from "../components/TextField";
import { EmptyState } from "../components/EmptyState";

const VARIANTS_HELPER =
  "Every parameter you swept in a backtest counts. Testing 200 variants and keeping the best one inflates its apparent edge; this number corrects for that.";

const TARGET_HELPER = "As a decimal, e.g. 0.015 = 1.5%.";

type FormState = {
  starting_capital: string; record_start_date: string; base_currency: string;
  risk_free_rate: string; trading_days_per_year: string; minimum_acceptable_return: string;
  benchmark_sharpe: string; confidence_level: string; strategy_variants_tested: string;
  daily_target_pct: string; weekly_target_pct: string; monthly_target_pct: string;
  risk_by_timeframe: Record<Timeframe, string>;
};

function toForm(s: SettingsT): FormState {
  return {
    starting_capital: s.starting_capital, record_start_date: s.record_start_date, base_currency: s.base_currency,
    risk_free_rate: s.risk_free_rate, trading_days_per_year: String(s.trading_days_per_year),
    minimum_acceptable_return: s.minimum_acceptable_return, benchmark_sharpe: s.benchmark_sharpe,
    confidence_level: s.confidence_level, strategy_variants_tested: String(s.strategy_variants_tested),
    daily_target_pct: s.daily_target_pct, weekly_target_pct: s.weekly_target_pct,
    monthly_target_pct: s.monthly_target_pct,
    risk_by_timeframe: s.risk_by_timeframe as Record<Timeframe, string>,
  };
}

export default function Settings() {
  const { data, isLoading } = useSettings();
  const update = useUpdateSettings();
  const [form, setForm] = useState<FormState | null>(null);

  useEffect(() => {
    if (data) setForm(toForm(data));
  }, [data]);

  function set<K extends keyof FormState>(key: K, value: string) {
    setForm((f) => (f ? { ...f, [key]: value } : f));
  }

  function setTfRisk(tf: Timeframe, value: string) {
    setForm((f) => (f ? { ...f, risk_by_timeframe: { ...f.risk_by_timeframe, [tf]: value } } : f));
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!form) return;
    update.mutate({
      starting_capital: form.starting_capital, record_start_date: form.record_start_date,
      base_currency: form.base_currency, risk_free_rate: form.risk_free_rate,
      trading_days_per_year: Number(form.trading_days_per_year),
      minimum_acceptable_return: form.minimum_acceptable_return, benchmark_sharpe: form.benchmark_sharpe,
      confidence_level: form.confidence_level, strategy_variants_tested: Number(form.strategy_variants_tested),
      daily_target_pct: form.daily_target_pct, weekly_target_pct: form.weekly_target_pct,
      monthly_target_pct: form.monthly_target_pct,
      risk_by_timeframe: form.risk_by_timeframe,
    });
  }

  if (isLoading || !form) return <EmptyState title="Settings" body="Loading settings…" />;

  return (
    <div>
      <SectionHeader title="Settings" />
      <form className="card page-section" onSubmit={handleSubmit}>
        <div className="form-row">
          <TextField label="Starting capital" type="number" step="0.01" value={form.starting_capital} onChange={(e) => set("starting_capital", e.target.value)} />
          <TextField label="Base currency" maxLength={3} value={form.base_currency} onChange={(e) => set("base_currency", e.target.value.toUpperCase())} />
        </div>
        <div className="form-row">
          <TextField label="Record start date" type="date" value={form.record_start_date} onChange={(e) => set("record_start_date", e.target.value)} />
          <TextField label="Trading days per year" type="number" value={form.trading_days_per_year} onChange={(e) => set("trading_days_per_year", e.target.value)} />
        </div>
        <div className="form-row">
          <TextField label="Risk-free rate" type="number" step="0.0001" value={form.risk_free_rate} onChange={(e) => set("risk_free_rate", e.target.value)} />
          <TextField label="Benchmark Sharpe" type="number" step="0.01" value={form.benchmark_sharpe} onChange={(e) => set("benchmark_sharpe", e.target.value)} />
        </div>
        <div className="form-row">
          <TextField label="Minimum acceptable return" type="number" step="0.0001" value={form.minimum_acceptable_return} onChange={(e) => set("minimum_acceptable_return", e.target.value)} />
          <TextField label="Confidence level" type="number" step="0.01" value={form.confidence_level} onChange={(e) => set("confidence_level", e.target.value)} />
        </div>
        <TextField
          label="Strategy variants tested"
          type="number"
          value={form.strategy_variants_tested}
          onChange={(e) => set("strategy_variants_tested", e.target.value)}
          helperText={VARIANTS_HELPER}
        />

        <SectionHeader title="Target rhythm" />
        <div className="form-row">
          <TextField
            label="Daily target"
            type="number"
            step="0.0001"
            value={form.daily_target_pct}
            onChange={(e) => set("daily_target_pct", e.target.value)}
            helperText={TARGET_HELPER}
          />
          <TextField
            label="Weekly target"
            type="number"
            step="0.0001"
            value={form.weekly_target_pct}
            onChange={(e) => set("weekly_target_pct", e.target.value)}
            helperText={TARGET_HELPER}
          />
        </div>
        <TextField
          label="Monthly target"
          type="number"
          step="0.0001"
          value={form.monthly_target_pct}
          onChange={(e) => set("monthly_target_pct", e.target.value)}
          helperText={TARGET_HELPER}
        />

        <SectionHeader title="Risk by timeframe" />
        <p className="page-lede">
          Smaller timeframes have worse signal-to-noise. Set the maximum risk per trade allowed at each timeframe, as a
          decimal of account equity (e.g. 0.005 = 0.5%). Trade Entry enforces this at save time.
        </p>
        <div className="form-grid form-grid--tf-risk">
          {TIMEFRAME_OPTIONS.map((tf) => (
            <TextField
              key={tf}
              label={tf}
              type="number"
              step="0.0001"
              min="0"
              value={form.risk_by_timeframe[tf] ?? ""}
              onChange={(e) => setTfRisk(tf, e.target.value)}
              helperText={`= ${pctOf(form.risk_by_timeframe[tf])}`}
            />
          ))}
        </div>

        <div className="form-actions">
          <Button type="submit" disabled={update.isPending}>{update.isPending ? "Saving…" : "Save settings"}</Button>
        </div>
      </form>

      <TargetsSection />
    </div>
  );
}

function TargetsSection() {
  const { data: targets, isLoading } = useTargets();
  const upsert = useUpsertTarget();
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("");

  function addTarget(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!name.trim() || !value.trim() || !unit.trim()) return;
    upsert.mutate({ metric_name: name.trim(), target_value: value, unit: unit.trim() }, {
      onSuccess: () => { setName(""); setValue(""); setUnit(""); },
    });
  }

  return (
    <div>
      <SectionHeader title="Targets" />
      {isLoading ? (
        <p className="page-lede">Loading targets…</p>
      ) : !targets?.length ? (
        <p className="page-lede">No targets set yet. Add one below.</p>
      ) : (
        <table className="data-table page-section">
          <thead><tr><th>Metric</th><th>Target</th><th>Unit</th></tr></thead>
          <tbody>
            {targets.map((t) => (
              <tr key={t.id}><td>{t.metric_name}</td><td className="data-table__num">{t.target_value}</td><td>{t.unit}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      <form className="form-row card" onSubmit={addTarget}>
        <TextField label="Metric name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. sharpe" />
        <TextField label="Target value" type="number" step="0.01" value={value} onChange={(e) => setValue(e.target.value)} />
        <TextField label="Unit" value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="e.g. ratio, pct" />
        <Button type="submit" disabled={upsert.isPending}>{upsert.isPending ? "Saving…" : "Save target"}</Button>
      </form>
    </div>
  );
}

function pctOf(decimalStr: string): string {
  const v = Number(decimalStr);
  return Number.isFinite(v) ? `${(v * 100).toFixed(3)}%` : "—";
}
