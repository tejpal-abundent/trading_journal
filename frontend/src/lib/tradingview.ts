/**
 * Pure helpers for TradingView URL/symbol parsing.
 * No DOM access. No side effects.
 */

/**
 * Convert a tradingview.com/x/HASH/ URL into the canonical PNG snapshot URL.
 * Returns null if the URL doesn't match the snapshot pattern.
 *
 * Examples that match:
 *   https://www.tradingview.com/x/abc123/
 *   https://www.tradingview.com/x/abc123
 *   tradingview.com/x/abc123?foo=bar
 */
export function parseTradingViewSnapshot(url: string): string | null {
  if (!url) return null;
  const m = url.match(/tradingview\.com\/x\/([A-Za-z0-9]+)/);
  return m ? `https://s3.tradingview.com/snapshots/x/${m[1]}.png` : null;
}

/**
 * Map the journal's timeframe codes to TradingView interval strings.
 * Unknown codes fall back to daily ("D").
 */
export function timeframeToInterval(tf: string): string {
  const map: Record<string, string> = {
    "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "2h": "120", "4h": "240", "6h": "360",
    "1d": "D", "3d": "3D", "1w": "W", "1M": "M",
  };
  return map[tf] ?? "D";
}

/**
 * Best-effort exchange-prefix the symbol for the TradingView widget.
 * If the pair already contains a colon (e.g. "BINANCE:BTCUSDT"), return as-is.
 * Otherwise assume crypto and prefix with BINANCE:.
 */
export function exchangePrefixedSymbol(pair: string): string {
  if (pair.includes(":")) return pair;
  return `BINANCE:${pair}`;
}
