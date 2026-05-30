import { useEffect, useRef, useState } from "react";
import { parseTradingViewSnapshot, timeframeToInterval, exchangePrefixedSymbol } from "../lib/tradingview";

interface Props {
  snapshotUrl: string;
  symbol: string;       // e.g. "BTCUSDT"
  timeframe: string;    // e.g. "15m"
}

export default function ChartEmbed({ snapshotUrl, symbol, timeframe }: Props) {
  const snapshotPng = parseTradingViewSnapshot(snapshotUrl || "");
  const [imgFailed, setImgFailed] = useState(false);

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
      {snapshotUrl && (!snapshotPng || imgFailed) && (
        <a href={snapshotUrl} target="_blank" rel="noreferrer" className="text-sm">
          📈 Open chart ↗
        </a>
      )}
      <div className="card" style={{ padding: 8 }}>
        <div className="text-xs text-2" style={{ marginBottom: 6 }}>Live now</div>
        <LiveWidget symbol={symbol} timeframe={timeframe} />
      </div>
    </div>
  );
}

function LiveWidget({ symbol, timeframe }: { symbol: string; timeframe: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    containerRef.current.innerHTML = "";
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: exchangePrefixedSymbol(symbol),
      interval: timeframeToInterval(timeframe),
      timezone: "Etc/UTC",
      theme: "dark",
      style: "1",
      locale: "en",
      hide_side_toolbar: false,
      allow_symbol_change: false,
      withdateranges: true,
      save_image: false,
    });
    containerRef.current.appendChild(script);
  }, [symbol, timeframe]);

  return (
    <div
      ref={containerRef}
      className="tradingview-widget-container"
      style={{ width: "100%", height: 400 }}
    />
  );
}
