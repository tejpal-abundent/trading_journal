import { Expectancy } from "../api";
import { formatCurrency } from "../lib/dashboard";

interface Props {
  expectancy: Expectancy;
}

export default function EdgeCard({ expectancy: e }: Props) {
  const v = e.value;
  const color = v > 0 ? "var(--green)" : v < 0 ? "var(--red)" : "var(--text2)";
  const confidence =
    e.trades >= 100 ? "strong" :
    e.trades >= 30  ? "reasonable" :
    e.trades >= 10  ? "noisy" : "very noisy";

  return (
    <div className="card" style={{
      borderLeft: `4px solid ${color}`,
      padding: 24,
    }}>
      <div className="text-xs text-2" style={{ letterSpacing: 1, textTransform: "uppercase" }}>
        Your edge
      </div>
      <div className="font-500" style={{
        fontSize: 48, color, marginTop: 8, lineHeight: 1,
      }}>
        {v >= 0 ? "+" : ""}{formatCurrency(v)} <span style={{ fontSize: 20, color: "var(--text2)" }}>/ trade</span>
      </div>
      <div className="text-sm text-2" style={{ marginTop: 8 }}>
        across {e.trades} trade{e.trades === 1 ? "" : "s"} · <span style={{ fontStyle: "italic" }}>{confidence}</span>
      </div>
      {e.trades > 0 && (
        <div className="text-sm" style={{ marginTop: 12, color: "var(--text2)" }}>
          You win <b style={{ color: "var(--text)" }}>{Math.round(e.win_rate * 100)}%</b> × {formatCurrency(e.avg_win)}
          {" — "}
          lose <b style={{ color: "var(--text)" }}>{Math.round(e.loss_rate * 100)}%</b> × {formatCurrency(e.avg_loss)}
          {" = "}
          <b style={{ color }}>{v >= 0 ? "+" : ""}{formatCurrency(v)}</b>
        </div>
      )}
      {e.last_trade_delta !== null && (
        <div className="text-xs" style={{
          marginTop: 8,
          color: e.last_trade_delta > 0 ? "var(--green)" : e.last_trade_delta < 0 ? "var(--red)" : "var(--text2)",
        }}>
          {e.last_trade_delta > 0 ? "↗" : e.last_trade_delta < 0 ? "↘" : "→"} Last trade: {e.last_trade_delta >= 0 ? "+" : ""}{formatCurrency(e.last_trade_delta)} to your edge
        </div>
      )}
    </div>
  );
}
