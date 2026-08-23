/**
 * Tiny inline-SVG bar histogram. No deps.
 * Bars centered around zero on the x-axis so negative values render left,
 * positive right — matches the mental model for R-multiple distributions.
 */
export function MiniHistogram({
  values,
  buckets = 12,
  width = 200,
  height = 44,
}: {
  values: number[];
  buckets?: number;
  width?: number;
  height?: number;
}) {
  if (!values || values.length === 0) {
    return (
      <svg width={width} height={height} role="img" aria-label="Histogram (no data)">
        <line
          x1="0"
          y1={height / 2}
          x2={width}
          y2={height / 2}
          stroke="var(--ground-3)"
          strokeWidth="1"
          strokeDasharray="2 3"
        />
      </svg>
    );
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  // Symmetric span around zero when values cross zero
  const bound = Math.max(Math.abs(min), Math.abs(max));
  const lo = min < 0 ? -bound : min;
  const hi = max > 0 ? bound : max;
  const span = hi - lo || 1;

  const bins = new Array(buckets).fill(0);
  for (const v of values) {
    const idx = Math.min(buckets - 1, Math.floor(((v - lo) / span) * buckets));
    bins[idx]++;
  }
  const peak = Math.max(...bins) || 1;

  const pad = 2;
  const barW = (width - pad * 2) / buckets;
  const zeroX = pad + ((0 - lo) / span) * (width - pad * 2);

  return (
    <svg width={width} height={height} role="img" aria-label="Distribution histogram">
      {/* zero axis */}
      <line
        x1={zeroX}
        y1={pad}
        x2={zeroX}
        y2={height - pad}
        stroke="var(--ground-3)"
        strokeWidth="1"
      />
      {bins.map((count, i) => {
        const binMid = lo + (i + 0.5) * (span / buckets);
        const isPos = binMid >= 0;
        const barH = ((count / peak) * (height - pad * 2)) || 0;
        const x = pad + i * barW + 0.5;
        const y = height - pad - barH;
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={Math.max(1, barW - 1)}
            height={barH}
            fill={isPos ? "var(--gain)" : "var(--loss)"}
            opacity={count === 0 ? 0.15 : 0.85}
          />
        );
      })}
    </svg>
  );
}
