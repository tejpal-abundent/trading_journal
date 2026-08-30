import { useMemo, useState } from "react";
import { SectionHeader } from "../components/SectionHeader";
import { MetricCard } from "../components/MetricCard";
import { EmptyState } from "../components/EmptyState";
import { HabitRow } from "../components/HabitRow";
import { SegmentedControl } from "../components/SegmentedControl";
import {
  useHabitMonth, useToggleHabit, useDeleteHabitLog,
  useCreateDefinition, useUpdateDefinition, useDeleteDefinition,
  type HabitCategory, type HabitDefinition,
} from "../hooks/useHabits";
import "../design/components.css";

const CATEGORY_LABELS: Record<HabitCategory, string> = {
  trading: "Trading",
  personal: "Personal",
  body: "Body",
  sleep: "Sleep",
};
const CATEGORY_ORDER: HabitCategory[] = ["trading", "personal", "body", "sleep"];

type MonthSelection = { year: number; month: number } | "all";

function monthValue(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}`;
}

function monthLabel(year: number, month: number): string {
  return new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString("en-US", {
    month: "long", year: "numeric", timeZone: "UTC",
  });
}

/** Range spanning back 12 months + current + forward 12 months. Ordered
 * newest → oldest so the current month sits near the top of the dropdown
 * with future months just above it (for planning ahead) and history below. */
function monthRange(currentYear: number, currentMonth: number, back = 12, forward = 12): { year: number; month: number }[] {
  const out: { year: number; month: number }[] = [];
  let y = currentYear;
  let m = currentMonth + forward;
  while (m > 12) { m -= 12; y += 1; }
  for (let i = 0; i < back + forward + 1; i++) {
    out.push({ year: y, month: m });
    m -= 1;
    if (m === 0) { m = 12; y -= 1; }
  }
  return out;
}

function slugifyKey(label: string): string {
  const base = label
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return (base || "habit").slice(0, 50);
}

/** Small inline form for adding a new habit — lives in the management row
 * at the bottom of the page rather than as its own component, since it's
 * just a couple of fields feeding useCreateDefinition. */
function AddHabitForm({ onClose }: { onClose: () => void }) {
  const [label, setLabel] = useState("");
  const [category, setCategory] = useState<HabitCategory>("trading");
  const [error, setError] = useState<string | null>(null);
  const createDefinition = useCreateDefinition();

  async function handleSubmit() {
    const trimmed = label.trim();
    if (!trimmed) return;
    setError(null);
    const baseKey = slugifyKey(trimmed);
    try {
      await createDefinition.mutateAsync({ key: baseKey, label: trimmed, category, sort_order: 1000 });
      onClose();
    } catch {
      try {
        await createDefinition.mutateAsync({
          key: `${baseKey}_${Date.now().toString(36)}`, label: trimmed, category, sort_order: 1000,
        });
        onClose();
      } catch {
        setError("Couldn't add that habit — try a different name.");
      }
    }
  }

  return (
    <div className="habit-add-form">
      <input
        className="field__input"
        placeholder="What do you want to track?"
        value={label}
        autoFocus
        onChange={(e) => setLabel(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
      />
      <select
        className="field__input habit-add-form__select"
        value={category}
        onChange={(e) => setCategory(e.target.value as HabitCategory)}
      >
        {CATEGORY_ORDER.map((c) => (
          <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
        ))}
      </select>
      <button type="button" className="btn btn--primary" onClick={handleSubmit} disabled={!label.trim()}>
        Add
      </button>
      <button type="button" className="btn btn--secondary" onClick={onClose}>
        Cancel
      </button>
      {error && <span className="field__error">{error}</span>}
    </div>
  );
}

/** One month rendered as a habit grid. Owns its own data fetch (useHabitMonth)
 * so the Year view can stack twelve of these without a dedicated year endpoint.
 * All the mutation handlers + editing state are lifted from the parent to keep
 * behaviour identical whether you're on Month view or Year view. */
function MonthPanel({
  year, month,
  editingId, onStartEdit, onCancelEdit,
  onSetStatus, onClear, onRename, onMove, onRetire,
}: {
  year: number; month: number;
  editingId: string | null;
  onStartEdit: (id: string) => void;
  onCancelEdit: () => void;
  onSetStatus: (habitId: string, date: string, status: boolean) => void;
  onClear: (habitId: string, date: string) => void;
  onRename: (habitId: string, label: string) => void;
  onMove: (definition: HabitDefinition, direction: "up" | "down") => void;
  onRetire: (habitId: string) => void;
}) {
  const { data, isLoading } = useHabitMonth(year, month);
  const byCategory: Record<HabitCategory, HabitDefinition[]> = { trading: [], personal: [], body: [], sleep: [] };
  if (data) for (const def of data.definitions) byCategory[def.category].push(def);
  if (isLoading || !data) {
    return <div className="page-section habit-card habit-month-panel">
      <div className="habit-month-panel__header">{monthLabel(year, month)}</div>
      <p className="page-lede">Loading…</p>
    </div>;
  }
  return (
    <div className="page-section habit-month-panel">
      <div className="habit-month-panel__header">{monthLabel(year, month)}</div>
      {CATEGORY_ORDER.map((category) => {
        const habits = byCategory[category];
        if (habits.length === 0) return null;
        return (
          <div key={category} className="habit-month-panel__category">
            <div className="habit-card__header">{CATEGORY_LABELS[category]}</div>
            {habits.map((definition) => (
              <HabitRow
                key={definition.id}
                definition={definition}
                days={data.days}
                entries={data.entries[definition.id] ?? {}}
                streak={data.stats[definition.id]?.current_streak ?? 0}
                isEditing={editingId === definition.id}
                onStartEdit={() => onStartEdit(definition.id)}
                onCancelEdit={onCancelEdit}
                onSetStatus={(date, status) => onSetStatus(definition.id, date, status)}
                onClear={(date) => onClear(definition.id, date)}
                onRename={(label) => onRename(definition.id, label)}
                onMove={(direction) => onMove(definition, direction)}
                onRetire={() => onRetire(definition.id)}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
}


export default function Habits() {
  const today = useMemo(() => new Date(), []);
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth() + 1;

  const [selection, setSelection] = useState<MonthSelection>({ year: currentYear, month: currentMonth });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [addingHabit, setAddingHabit] = useState(false);
  const [viewMode, setViewMode] = useState<"month" | "year">("month");

  const displayYear = selection === "all" ? currentYear : selection.year;
  const displayMonth = selection === "all" ? currentMonth : selection.month;
  const isCurrentMonth = displayYear === currentYear && displayMonth === currentMonth;

  const { data, isLoading } = useHabitMonth(displayYear, displayMonth);
  const toggleHabit = useToggleHabit();
  const deleteLog = useDeleteHabitLog();
  const updateDefinition = useUpdateDefinition();
  const deleteDefinition = useDeleteDefinition();

  const monthOptions = useMemo(() => monthRange(currentYear, currentMonth), [currentYear, currentMonth]);

  function shiftMonth(direction: 1 | -1) {
    const base = selection === "all" ? { year: currentYear, month: currentMonth } : selection;
    let { year, month } = base;
    month += direction;
    if (month === 0) {
      month = 12;
      year -= 1;
    } else if (month === 13) {
      month = 1;
      year += 1;
    }
    setSelection({ year, month });
  }

  if (isLoading || !data) {
    return <EmptyState title="Habits" body="Loading this month…" />;
  }

  const byCategory: Record<HabitCategory, HabitDefinition[]> = { trading: [], personal: [], body: [], sleep: [] };
  for (const def of data.definitions) {
    byCategory[def.category].push(def);
  }

  const answeredDays = new Set<string>();
  Object.values(data.entries).forEach((byDate) => {
    Object.keys(byDate).forEach((d) => answeredDays.add(d));
  });

  const elapsedDays = isCurrentMonth ? today.getDate() : data.days.length;
  const statValues = Object.values(data.stats);
  const overallCompletion = statValues.length
    ? statValues.reduce((sum, s) => sum + s.completion_pct_this_month, 0) / statValues.length
    : 0;

  let bestStreak = 0;
  let bestStreakLabel = "";
  for (const def of data.definitions) {
    const s = data.stats[def.id];
    if (s && s.current_streak > bestStreak) {
      bestStreak = s.current_streak;
      bestStreakLabel = def.label;
    }
  }

  function reorder(definition: HabitDefinition, direction: "up" | "down") {
    const siblings = byCategory[definition.category];
    const idx = siblings.findIndex((d) => d.id === definition.id);
    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= siblings.length) return;
    const neighbor = siblings[swapIdx];
    updateDefinition.mutate({ id: definition.id, sort_order: neighbor.sort_order });
    updateDefinition.mutate({ id: neighbor.id, sort_order: definition.sort_order });
  }

  return (
    <div>
      <SectionHeader
        title="Habits"
        action={
          <div className="year-switcher">
            <SegmentedControl
              options={[
                { value: "month", label: "Month" },
                { value: "year", label: "Year" },
              ]}
              value={viewMode}
              onChange={(v) => setViewMode(v as "month" | "year")}
            />
            {viewMode === "month" && (
              <>
                <button type="button" className="btn btn--secondary" onClick={() => shiftMonth(-1)}>
                  ←
                </button>
                <select
                  className="field__input habit-month-select"
                  value={selection === "all" ? "all" : monthValue(selection.year, selection.month)}
                  onChange={(e) => {
                    if (e.target.value === "all") {
                      setSelection("all");
                    } else {
                      const [y, m] = e.target.value.split("-").map(Number);
                      setSelection({ year: y, month: m });
                    }
                  }}
                >
                  {monthOptions.map((opt) => (
                    <option key={monthValue(opt.year, opt.month)} value={monthValue(opt.year, opt.month)}>
                      {monthLabel(opt.year, opt.month)}
                    </option>
                  ))}
                  <option value="all">All time</option>
                </select>
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={() => shiftMonth(1)}
                  disabled={isCurrentMonth}
                >
                  →
                </button>
              </>
            )}
            {viewMode === "year" && (
              <select
                className="field__input habit-month-select"
                value={displayYear}
                onChange={(e) => setSelection({ year: Number(e.target.value), month: 1 })}
              >
                {[currentYear - 1, currentYear, currentYear + 1].map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            )}
          </div>
        }
      />
      <p className="page-lede">The small things, ticked daily.</p>

      {viewMode === "year" && (
        <div>
          <p className="page-lede">Every month of {displayYear} in one scroll. Tick as you go, or backfill anytime.</p>
          {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
            <MonthPanel
              key={`${displayYear}-${m}`}
              year={displayYear}
              month={m}
              editingId={editingId}
              onStartEdit={(id) => setEditingId(id)}
              onCancelEdit={() => setEditingId(null)}
              onSetStatus={(habitId, date, status) => toggleHabit.mutate({ date, habitId, status })}
              onClear={(habitId, date) => deleteLog.mutate({ date, habitId })}
              onRename={(habitId, label) => updateDefinition.mutate({ id: habitId, label })}
              onMove={(definition, direction) => reorder(definition, direction)}
              onRetire={(habitId) => {
                setEditingId(null);
                deleteDefinition.mutate(habitId);
              }}
            />
          ))}
          <div className="habit-manage-row">
            {addingHabit ? (
              <AddHabitForm onClose={() => setAddingHabit(false)} />
            ) : (
              <button type="button" className="btn btn--secondary" onClick={() => setAddingHabit(true)}>
                + Add habit
              </button>
            )}
          </div>
        </div>
      )}

      {viewMode === "month" && <>
      <div className="metric-grid-3">
        <MetricCard
          label="Completion this month"
          value={`${overallCompletion.toFixed(0)}%`}
          n={statValues.length}
        />
        <MetricCard
          label="Best streak"
          value={bestStreak > 0 ? `${bestStreak}d` : "—"}
          n={bestStreak}
          sub={bestStreakLabel || undefined}
        />
        <MetricCard
          label="Days answered"
          value={`${answeredDays.size} / ${elapsedDays}`}
          n={answeredDays.size}
          sub={monthLabel(displayYear, displayMonth)}
        />
      </div>

      {answeredDays.size === 0 && (
        <p className="habit-empty-copy">A new month. What did you do today?</p>
      )}

      {CATEGORY_ORDER.map((category) => {
        const habits = byCategory[category];
        if (habits.length === 0) return null;
        return (
          <div key={category} className="page-section habit-card">
            <div className="habit-card__header">{CATEGORY_LABELS[category]}</div>
            {habits.map((definition) => (
              <HabitRow
                key={definition.id}
                definition={definition}
                days={data.days}
                entries={data.entries[definition.id] ?? {}}
                streak={data.stats[definition.id]?.current_streak ?? 0}
                isEditing={editingId === definition.id}
                onStartEdit={() => setEditingId(definition.id)}
                onCancelEdit={() => setEditingId(null)}
                onSetStatus={(date, status) =>
                  toggleHabit.mutate({ date, habitId: definition.id, status })
                }
                onClear={(date) => deleteLog.mutate({ date, habitId: definition.id })}
                onRename={(label) => updateDefinition.mutate({ id: definition.id, label })}
                onMove={(direction) => reorder(definition, direction)}
                onRetire={() => {
                  setEditingId(null);
                  deleteDefinition.mutate(definition.id);
                }}
              />
            ))}
          </div>
        );
      })}

      <div className="habit-manage-row">
        {addingHabit ? (
          <AddHabitForm onClose={() => setAddingHabit(false)} />
        ) : (
          <button type="button" className="btn btn--secondary" onClick={() => setAddingHabit(true)}>
            + Add habit
          </button>
        )}
      </div>
      </>}
    </div>
  );
}
