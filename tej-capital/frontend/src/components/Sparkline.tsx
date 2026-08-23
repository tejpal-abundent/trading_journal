/**
 * Tiny inline-SVG line sparkline. No external dependencies.
 * Renders an area fill below the line at 15% opacity + the line itself.
 */
export function Sparkline({
  data,
  width = 140,
  height = 36,
  color,
}: {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}) {
  if (!data || data.length < 2) {
    return (
      <svg width={width} height={height} role="img" aria-label="Sparkline (not enough data)">
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
  const stroke = color ?? "var(--accent)";
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pad = 2;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const points = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * w;
    const y = pad + (1 - (v - min) / span) * h;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  const linePath = `M ${points.join(" L ")}`;
  const areaPath = `${linePath} L ${pad + w},${pad + h} L ${pad},${pad + h} Z`;
  return (
    <svg width={width} height={height} role="img" aria-label="Sparkline">
      <path d={areaPath} fill={stroke} opacity="0.15" />
      <path d={linePath} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
