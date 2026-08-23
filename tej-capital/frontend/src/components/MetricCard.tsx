import type { ReactNode } from "react";
import "../design/components.css";

export function MetricCard({ label, value, n, sub, tone, chip }: {
  label: string; value: string; n: number;
  sub?: string; tone?: "neutral" | "gain" | "loss"; chip?: ReactNode;
}) {
  return (
    <div className={`metric metric--${tone ?? "neutral"}`}>
      <div className="metric__label">{label}</div>
      <div className="metric__value">{value}</div>
      <div className="metric__meta">
        {sub && <span className="metric__sub">{sub}</span>}
        <span className="metric__n">N={n}</span>
      </div>
      {chip && <div className="metric__chip-row">{chip}</div>}
    </div>
  );
}
