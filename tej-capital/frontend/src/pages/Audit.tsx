import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAudit, type AuditFeedItem } from "../hooks/useAudit";
import { SectionHeader } from "../components/SectionHeader";
import { EmptyState } from "../components/EmptyState";
import { formatDateLong } from "../lib/format";

type Chip = "correction" | "amendment" | "override" | "superseded";

const CHIPS: { value: Chip; label: string }[] = [
  { value: "correction", label: "Correction" },
  { value: "amendment", label: "Amendment" },
  { value: "override", label: "Override" },
  { value: "superseded", label: "Superseded" },
];

function matchesChip(item: AuditFeedItem, chip: Chip): boolean {
  if (chip === "correction") return item.type === "correction";
  if (chip === "amendment") return item.type === "amendment";
  if (chip === "override") return item.type === "amendment" && item.details.is_override_during_drawdown === true;
  // "Superseded" — every correction row exists because a prior row was
  // superseded, so it shares the correction set (the feed has no separate
  // superseded-row type of its own).
  return item.type === "correction";
}

function resultingRowLink(item: AuditFeedItem): { label: string; href: string } | null {
  if (item.type === "correction") {
    const table = String(item.details.table_name ?? "");
    const rowId = String(item.details.superseded_by_row_id ?? "");
    if (!rowId) return null;
    return { label: `${table} → ${rowId.slice(0, 8)}…`, href: "/ledger" };
  }
  const newLimitId = String(item.details.new_limit_id ?? "");
  if (!newLimitId) return null;
  return { label: `policy limit → ${newLimitId.slice(0, 8)}…`, href: "/policy" };
}

export default function Audit() {
  const { data, isLoading } = useAudit();
  const [active, setActive] = useState<Set<Chip>>(new Set());

  function toggle(chip: Chip) {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(chip)) next.delete(chip);
      else next.add(chip);
      return next;
    });
  }

  const rows = useMemo(() => {
    const all = data ?? [];
    if (active.size === 0) return all;
    return all.filter((item) => Array.from(active).some((c) => matchesChip(item, c)));
  }, [data, active]);

  const correctionCount = (data ?? []).filter((i) => i.type === "correction").length;
  const spanDays = useMemo(() => {
    if (!data || data.length < 2) return null;
    const dates = data.map((i) => new Date(i.occurred_at).getTime());
    return Math.round((Math.max(...dates) - Math.min(...dates)) / 86_400_000);
  }, [data]);

  return (
    <div>
      <SectionHeader title="Audit Trail" />

      {correctionCount > 0 && (
        <div className="banner banner--info page-section">
          Your record has {correctionCount} correction{correctionCount === 1 ? "" : "s"}
          {spanDays != null ? ` across ${spanDays} days` : ""}, each with a stated reason. Allocators expect
          corrections. What they check is whether you disclosed them.
        </div>
      )}

      <div className="chip-row">
        {CHIPS.map((c) => (
          <button
            key={c.value}
            type="button"
            className={`chip-toggle${active.has(c.value) ? " chip-toggle--active" : ""}`}
            onClick={() => toggle(c.value)}
          >
            {c.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <EmptyState title="Audit Trail" body="Loading the audit feed…" />
      ) : rows.length === 0 ? (
        <EmptyState title="Nothing recorded yet" body="Corrections and policy amendments will appear here as they happen." />
      ) : (
        <table className="data-table">
          <thead><tr><th>Date</th><th>Type</th><th>Table</th><th>Reason</th><th>Resulting row</th></tr></thead>
          <tbody>
            {rows.map((item) => {
              const link = resultingRowLink(item);
              return (
                <tr key={item.id}>
                  <td>{formatDateLong(item.occurred_at.slice(0, 10))}</td>
                  <td>{item.type}</td>
                  <td>{String(item.details.table_name ?? "policy")}</td>
                  <td>{item.reason}</td>
                  <td>{link ? <Link to={link.href}>{link.label}</Link> : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
