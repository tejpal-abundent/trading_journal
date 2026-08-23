/**
 * Semicircle gauge with tinted zones + needle. Inline SVG, no deps.
 * Used for Sharpe / Sortino to make "is this good?" readable at a glance.
 */
type Zone = { from: number; to: number; color: string };

export function Gauge({
  value,
  min,
  max,
  zones,
  width = 140,
  height = 82,
}: {
  value: number | null;
  min: number;
  max: number;
  zones: Zone[];
  width?: number;
  height?: number;
}) {
  const cx = width / 2;
  const cy = height - 8;
  const r = Math.min(cx - 8, height - 12);
  const startAngle = Math.PI;
  const endAngle = 0;
  const range = max - min;

  const angleFor = (v: number) => {
    const t = Math.max(0, Math.min(1, (v - min) / range));
    return startAngle - t * (startAngle - endAngle);
  };
  const point = (angle: number, radius: number) => ({
    x: cx + Math.cos(angle) * radius,
    y: cy - Math.sin(angle) * radius,
  });
  const arcPath = (from: number, to: number, radius: number) => {
    const a1 = angleFor(from);
    const a2 = angleFor(to);
    const p1 = point(a1, radius);
    const p2 = point(a2, radius);
    const largeArc = Math.abs(a1 - a2) > Math.PI ? 1 : 0;
    return `M ${p1.x.toFixed(2)},${p1.y.toFixed(2)} A ${radius},${radius} 0 ${largeArc} 1 ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
  };

  return (
    <svg width={width} height={height} role="img" aria-label={`Gauge: ${value ?? "n/a"} on ${min} to ${max}`}>
      {/* track */}
      <path d={arcPath(min, max, r)} stroke="var(--ground-3)" strokeWidth="8" fill="none" strokeLinecap="round" />
      {/* zones */}
      {zones.map((z, i) => (
        <path
          key={i}
          d={arcPath(z.from, z.to, r)}
          stroke={z.color}
          strokeWidth="8"
          fill="none"
          opacity="0.9"
        />
      ))}
      {/* needle */}
      {value !== null && (() => {
        const needleAngle = angleFor(Math.max(min, Math.min(max, value)));
        const tip = point(needleAngle, r - 2);
        return (
          <g>
            <line
              x1={cx}
              y1={cy}
              x2={tip.x}
              y2={tip.y}
              stroke="var(--ink-1)"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <circle cx={cx} cy={cy} r="3.5" fill="var(--ink-1)" />
          </g>
        );
      })()}
      {/* min / max labels */}
      <text
        x={point(startAngle, r).x}
        y={cy + 14}
        textAnchor="middle"
        fontSize="9"
        fontFamily="ui-monospace, monospace"
        fill="var(--ink-3)"
      >
        {min}
      </text>
      <text
        x={point(endAngle, r).x}
        y={cy + 14}
        textAnchor="middle"
        fontSize="9"
        fontFamily="ui-monospace, monospace"
        fill="var(--ink-3)"
      >
        {max}
      </text>
    </svg>
  );
}
