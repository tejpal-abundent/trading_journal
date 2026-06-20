import { useState } from "react";
import { parseTradingViewSnapshot } from "../lib/tradingview";

interface Props {
  snapshotUrl: string;
}

export default function ChartEmbed({ snapshotUrl }: Props) {
  const snapshotPng = parseTradingViewSnapshot(snapshotUrl || "");
  const [imgFailed, setImgFailed] = useState(false);

  if (!snapshotUrl) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {snapshotPng && !imgFailed && (
        <div className="card" style={{ padding: 8 }}>
          <div className="text-xs text-2" style={{ marginBottom: 6 }}>Your snapshot at trade time</div>
          <a href={snapshotUrl} target="_blank" rel="noreferrer">
            <img
              src={snapshotPng}
              alt="TradingView snapshot"
              style={{ width: "100%", borderRadius: 4, display: "block" }}
              onError={() => setImgFailed(true)}
            />
          </a>
        </div>
      )}
      {(!snapshotPng || imgFailed) && (
        <a href={snapshotUrl} target="_blank" rel="noreferrer" className="text-sm">
          📈 Open chart ↗
        </a>
      )}
    </div>
  );
}
