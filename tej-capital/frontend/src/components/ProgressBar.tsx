/**
 * Horizontal progress bar, 0..1 value. Track + fill + optional label above.
 */
export function ProgressBar({
  value,
  label,
  width = 200,
  height = 8,
}: {
  value: number | null;
  label?: string;
  width?: number;
  height?: number;
}) {
  const pct = value === null ? 0 : Math.max(0, Math.min(1, value)) * 100;
  const display = value === null ? "—" : `${(value * 100).toFixed(1)}%`;

  return (
    <div style={{ width, display: "flex", flexDirection: "column", gap: 4 }}>
      {label && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--size-micro)",
            color: "var(--ink-3)",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          <span>{label}</span>
          <span>{display}</span>
        </div>
      )}
      <div
        style={{
          width: "100%",
          height,
          background: "var(--ground-3)",
          borderRadius: "var(--radius-sm)",
          overflow: "hidden",
        }}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: "var(--accent)",
            transition: "width var(--duration-2) var(--ease-out)",
          }}
        />
      </div>
    </div>
  );
}
