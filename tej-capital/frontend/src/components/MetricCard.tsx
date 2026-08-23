import type { ReactNode } from "react";
import "../design/components.css";

export function MetricCard({ label, value, n, sub, tone, chip, info, visual }: {
  label: string;
  value: string;
  n: number;
  sub?: string;
  tone?: "neutral" | "gain" | "loss";
  chip?: ReactNode;
  info?: string;
  visual?: ReactNode;
}) {
  return (
    <div className={`metric metric--${tone ?? "neutral"}`}>
      <div className="metric__label-row">
        <span className="metric__label">{label}</span>
        {info && (
          <span className="metric__info" tabIndex={0} aria-label={info}>
            <span aria-hidden="true">ⓘ</span>
            <span className="metric__tooltip" role="tooltip">{info}</span>
          </span>
        )}
      </div>
      <div className="metric__value">{value}</div>
      {visual && <div className="metric__visual">{visual}</div>}
      <div className="metric__meta">
        {sub && <span className="metric__sub">{sub}</span>}
        <span className="metric__n">N={n}</span>
      </div>
      {chip && <div className="metric__chip-row">{chip}</div>}
    </div>
  );
}
