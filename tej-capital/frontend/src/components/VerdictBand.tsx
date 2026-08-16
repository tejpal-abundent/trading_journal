import "../design/components.css";

type Verdict = { headline: string; detail: string; level: "ok" | "caution" | "not_yet_meaningful"; n_days: number };

export function VerdictBand({ v }: { v: Verdict }) {
  return (
    <div className={`verdict verdict--${v.level}`} role="status">
      <div className="verdict__headline">{v.headline}</div>
      <div className="verdict__detail">{v.detail}</div>
      <div className="verdict__meta">N={v.n_days}</div>
    </div>
  );
}
