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
 * Case-insensitive. Accepts "4h", "4H", "4hr", "1d", "1D", etc.
 * Unknown codes fall back to daily ("D").
 */
export function timeframeToInterval(tf: string): string {
  const k = (tf || "").toLowerCase().replace(/hr$/, "h");
  const map: Record<string, string> = {
    "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "2h": "120", "4h": "240", "6h": "360", "12h": "720",
    "1d": "D", "3d": "3D", "1w": "W", "1mo": "M",
  };
  return map[k] ?? "D";
}

/**
 * Pass the symbol to TradingView as-is. TradingView will resolve unprefixed
 * symbols across asset classes (forex, crypto, equities). If the user wants
 * to force an exchange they can write e.g. "BINANCE:BTCUSDT" themselves.
 */
export function exchangePrefixedSymbol(pair: string): string {
  return pair;
}
